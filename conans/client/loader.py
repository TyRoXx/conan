from conans.errors import ConanException, NotFoundException
from conans.model.conan_file import ConanFile
import inspect
import uuid
import imp
import os
from conans.util.files import load
from conans.paths import CONANFILE_TXT
from conans.util.config_parser import ConfigParser
from conans.model.options import OptionsValues
from conans.model.ref import ConanFileReference
from conans.model.settings import Settings


class ConanFileLoader(object):
    def __init__(self, output, runner, settings, options):
        '''
        param settings: Settings object, to assign to ConanFile at load time
        param options: OptionsValues, necessary so the base conanfile loads the options
                        to start propagation, and having them in order to call build()
        '''

        self._output = output
        self._runner = runner
        assert isinstance(settings, Settings)
        assert isinstance(options, OptionsValues)
        self._settings = settings
        self._options = options

    def _create_check_conan(self, conan_file, consumer):
        """ Check the integrity of a given conanfile
        """
        result = None
        for name, attr in conan_file.__dict__.iteritems():
            if "_" in name:
                continue
            if inspect.isclass(attr) and issubclass(attr, ConanFile) and attr != ConanFile:
                if result is None:
                    # Actual instantiation of ConanFile object
                    result = attr(self._output, self._runner, self._settings.copy())
                else:
                    raise ConanException("More than 1 conanfile in the file")

        if result is None:
            raise ConanException("No subclass of ConanFile")

        # check name and version were specified
        if not consumer:
            if not hasattr(result, "name") or not result.name:
                raise ConanException("conanfile didn't specify name")
            if not hasattr(result, "version") or not result.version:
                raise ConanException("conanfile didn't specify version")

        return result

    def load_conan(self, conan_file_path, consumer=False):
        """ loads a ConanFile object from the given file
        """
        # Check if precompiled exist, delete it
        if os.path.exists(conan_file_path + "c"):
            os.unlink(conan_file_path + "c")

        if not os.path.exists(conan_file_path):
            raise NotFoundException("%s not found!" % conan_file_path)

        # We have to generate a new name for each conans
        module_id = uuid.uuid1()
        try:
            loaded = imp.load_source("conan_conan%s" % module_id, conan_file_path)
        except Exception:
            import traceback
            trace = traceback.format_exc().split('\n')
            raise ConanException("Unable to load conanfile in %s\n%s" % (conan_file_path,
                                                                         '\n'.join(trace[3:])))
        try:
            result = self._create_check_conan(loaded, consumer)
            if consumer:
                result.options.initialize_upstream(self._options)
            return result
        except Exception as e:  # re-raise with file name
            raise ConanException("%s: %s" % (conan_file_path, str(e)))

    def load_conan_txt(self, conan_requirements_path):

        if not os.path.exists(conan_requirements_path):
            raise NotFoundException("%s not found!" % CONANFILE_TXT)

        conanfile = ConanFile(self._output, self._runner, self._settings.copy())

        parser = ConanFileTextLoader(load(conan_requirements_path))
        for requirement_text in parser.requirements:
            ConanFileReference.loads(requirement_text)  # Raise if invalid
            conanfile.requires.add(requirement_text)

        conanfile.generators = parser.generators

        options = OptionsValues.loads(parser.options)
        conanfile.options.values = options
        conanfile.options.initialize_upstream(self._options)

        # imports method
        conanfile.imports = ConanFileTextLoader.imports_method(conanfile,
                                                               parser.import_parameters)

        return conanfile


class ConanFileTextLoader(object):
    """Parse a plain requirements file"""

    def __init__(self, input_text):
        # Prefer composition over inheritance, the __getattr__ was breaking things
        self._config_parser = ConfigParser(input_text,  ["requires", "generators", "options",
                                                         "imports"])

    @property
    def requirements(self):
        """returns a list of requires
        EX:  "OpenCV/2.4.10@phil/stable"
        """
        return [r.strip() for r in self._config_parser.requires.splitlines()]

    @property
    def options(self):
        return self._config_parser.options

    @property
    def import_parameters(self):
        ret = []
        local_install_text = self._config_parser.imports
        for local_install_line in local_install_text.splitlines():
            invalid_line_msg = "Invalid imports line: %s" \
                               "\nEX: OpenCV/lib, * -> ./lib" % local_install_line
            try:
                if local_install_line.startswith("/") or local_install_line.startswith(".."):
                    raise ConanException("Import's paths can't begin with '/' or '..'")
                pair = local_install_line.split("->")
                source = pair[0].strip().split(',', 1)
                dest = pair[1].strip()
                src, pattern = source[0].strip(), source[1].strip()
                ret.append((pattern, dest, src))
            except ConanException as excp:
                raise ConanException("%s\n%s" % (invalid_line_msg, excp.message))
            except:
                raise ConanException(invalid_line_msg)
        return ret

    @property
    def generators(self):
        return self._config_parser.generators.splitlines()

    @staticmethod
    def imports_method(conan_file, parameters):
        def imports():
            for import_params in parameters:
                conan_file.copy(*import_params)
        return imports
