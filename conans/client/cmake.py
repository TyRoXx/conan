from conans.errors import ConanException
from conans.model.settings import Settings


class CMake(object):

    def __init__(self, settings):
        assert isinstance(settings, Settings)
        self._settings = settings

    @staticmethod
    def options_cmd_line(options, option_upper=True, value_upper=True):
        result = []
        for option, value in options.values.as_list():
            if value is not None:
                option = option.upper() if option_upper else option
                value = value.upper() if value_upper else value
                result.append("-D%s=%s" % (option, value))
        return ' '.join(result)

    @property
    def generator(self):
        if (not self._settings.compiler or
            not self._settings.compiler.version or
            not self._settings.arch):
            raise ConanException("You must specify compiler, compiler.version and arch in "
                                 "your settings to use a CMake generator")

        if self._settings.compiler == "Visual Studio":
            base = "Visual Studio %s" % self._settings.compiler.version
            if self._settings.arch == "x86_64":
                return base + " Win64"
            elif self._settings.arch == "arm":
                return base + " ARM"
            else:
                return base

        if self._settings.os == "Windows":
            if self._settings.compiler == "gcc":
                if self._settings.compiler.version == "4.9":
                    return "Unix Makefiles"
                return "MinGW Makefiles"
            if self._settings.compiler in ["clang", "apple-clang"]:
                return "MinGW Makefiles"
        if self._settings.os == "Linux":
            if self._settings.compiler in ["gcc", "clang", "apple-clang"]:
                return "Unix Makefiles"
        if self._settings.os == "Macos":
            if self._settings.compiler in ["gcc", "clang", "apple-clang"]:
                return "Unix Makefiles"

        raise ConanException("Unknown cmake generator for these settings")

    @property
    def is_multi_configuration(self):
        """ some IDEs are multi-configuration, as Visual. Makefiles or Ninja are single-conf
        """
        if "Visual" in str(self._settings.compiler):
            return True
        # TODO: complete logic
        return False

    @property
    def command_line(self):
        return '-G "%s" %s %s %s -Wno-dev' % (self.generator, self.build_type,
                                     self.runtime, self.flags)

    @property
    def build_type(self):
        try:
            build_type = self._settings.build_type
        except ConanException:
            return ""
        if build_type and not self.is_multi_configuration:
            return "-DCMAKE_BUILD_TYPE=%s" % build_type
        return ""

    @property
    def build_config(self):
        """ cmake --build tool have a --config option for Multi-configuration IDEs
        """
        try:
            build_type = self._settings.build_type
        except ConanException:
            return ""
        if build_type and self.is_multi_configuration:
            return "--config %s" % build_type
        return ""

    @property
    def flags(self):
        op_system = self._settings.os
        arch = self._settings.arch
        comp = self._settings.compiler
        comp_version = self._settings.compiler.version

        flags = []
        if op_system == "Windows":
            if comp == "clang":
                flags.append("-DCMAKE_C_COMPILER=clang")
                flags.append("-DCMAKE_CXX_COMPILER=clang++")
        if comp:
            flags.append('-DCONAN_COMPILER="%s"' % comp)
        if comp_version:
            flags.append('-DCONAN_COMPILER_VERSION="%s"' % comp_version)
        if arch == "x86":
            if op_system == "Linux":
                flags.extend(["-DCONAN_CXX_FLAGS=-m32",
                             "-DCONAN_SHARED_LINK_FLAGS=-m32",
                             "-DCONAN_C_FLAGS=-m32"])
            elif op_system == "Macos":
                flags.append("-DCMAKE_OSX_ARCHITECTURES=i386")
        return " ".join(flags)

    @property
    def runtime(self):
        try:
            runtime = self._settings.compiler.runtime
        except ConanException:
            return ""
        if runtime:
            return "-DCONAN_LINK_RUNTIME=/%s" % runtime
        return ""
