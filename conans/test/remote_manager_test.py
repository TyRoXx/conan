import unittest
from conans.client.remote_manager import RemoteManager
from mock import Mock
from conans.errors import NotFoundException
from conans.model.ref import ConanFileReference, PackageReference
from conans.client.paths import ConanPaths
from conans.test.tools import TestBufferConanOutput
from conans.test.utils.test_files import temp_folder


class MockRemoteClient(object):

    def __init__(self):
        self.upload_package = Mock()
        self.get_conan_digest = Mock()
        self.get_conanfile = Mock()
        self.get_package = Mock(return_value=[("one.txt", "ONE")])
        self.remote_url = None

        self.raise_count = 0

    def upload_conan(self, *argc, **argv):  # @UnusedVariable
        if self.remote_url != "url3":
            self.raise_count += 1
            raise NotFoundException(self.remote_url)
        else:
            return self.remote_url


class RemoteManagerTest(unittest.TestCase):
    """Unit test"""

    def setUp(self):
        self.conan_reference = ConanFileReference.loads("openssl/2.0.3@lasote/testing")
        self.package_reference = PackageReference(self.conan_reference, "123123123")
        self.remote_client = MockRemoteClient()
        self.output = TestBufferConanOutput()
        self.paths = ConanPaths(temp_folder(), None, self.output)
        self.remotes = [("default", "url1"), ("other", "url2"), ("last", "url3")]
        self.manager = RemoteManager(self.paths, self.remotes, self.remote_client, self.output)

    def test_properties(self):
        # Remote names
        self.assertEquals(self.manager.remote_names, ["default", "other", "last"])
        # Remote url
        self.assertEquals(self.manager.remote_url("default"), "url1")
        self.assertEquals(self.manager.remote_url("other"), "url2")

    def remote_selection_test(self):
        # If no remote is specified will look to first
        self.assertRaises(NotFoundException, self.manager.upload_conan, self.conan_reference)

        # If remote is specified took it
        self.assertRaises(NotFoundException,
                          self.manager.upload_conan, self.conan_reference, "other")

    def method_called_test(self):
        self.assertFalse(self.remote_client.upload_package.called)
        self.manager.upload_package(self.package_reference, "other")
        self.assertTrue(self.remote_client.upload_package.called)

        self.assertFalse(self.remote_client.get_conan_digest.called)
        self.manager.get_conan_digest(self.conan_reference)
        self.assertTrue(self.remote_client.get_conan_digest.called)

        self.assertFalse(self.remote_client.get_conanfile.called)
        self.manager.get_conanfile(self.conan_reference)
        self.assertTrue(self.remote_client.get_conanfile.called)

        self.assertFalse(self.remote_client.get_package.called)
        self.manager.get_package(self.package_reference)
        self.assertTrue(self.remote_client.get_package.called)
