from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime
from conan.tools.scm import Version
from conan.tools.env import VirtualBuildEnv
import os

required_conan_version = ">=1.54.0"


class OatppConan(ConanFile):
    name = "oatpp"
    description = "Modern Web Framework for C++"
    homepage = "https://github.com/oatpp/oatpp"
    license = "Apache-2.0"
    topics = ("oat++", "web-framework")
    url = "https://github.com/conan-io/conan-center-index"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_test_library": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_test_library": False,
    }

    @property
    def _version(self):
        version = str(self.version)
        if version.endswith(".latest"):
            version = version[:-len(".latest")]
        return version

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)
        if self.settings.os == "Windows" and self.options.shared:
            raise ConanInvalidConfiguration("oatpp can not be built as shared library on Windows")

        if self.settings.compiler == "gcc" and Version(self.settings.compiler.version) < "5":
            raise ConanInvalidConfiguration("oatpp requires GCC >=5")

    def build_requirements(self):
        if Version(self._version) >= "1.3.0":
            self.tool_requires("cmake/[>=3.20 <4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["OATPP_BUILD_TESTS"] = False
        tc.variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = True
        if is_msvc(self) and Version(self.version) >= "1.3.0":
            tc.variables["OATPP_MSVC_LINK_STATIC_RUNTIME"] = is_msvc_static_runtime(self)
        tc.variables["OATPP_LINK_TEST_LIBRARY"] = self.options.with_test_library
        tc.generate()
        venv = VirtualBuildEnv(self)
        venv.generate(scope="build")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "oatpp")

        include_dir = os.path.join("include", f"oatpp-{self._version}", "oatpp")
        lib_dir = os.path.join("lib", f"oatpp-{self._version}")

        # oatpp
        self.cpp_info.components["_oatpp"].names["cmake_find_package"] = "oatpp"
        self.cpp_info.components["_oatpp"].names["cmake_find_package_multi"] = "oatpp"
        self.cpp_info.components["_oatpp"].set_property("cmake_target_name", "oatpp::oatpp")
        self.cpp_info.components["_oatpp"].includedirs = [include_dir]
        self.cpp_info.components["_oatpp"].libdirs = [lib_dir]
        self.cpp_info.components["_oatpp"].libs = ["oatpp"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["_oatpp"].system_libs = ["pthread", "m"]
        elif self.settings.os == "Windows":
            self.cpp_info.components["_oatpp"].system_libs = ["ws2_32", "wsock32"]

        # oatpp-test
        if self.options.with_test_library:
            self.cpp_info.components["oatpp-test"].names["cmake_find_package"] = "oatpp-test"
            self.cpp_info.components["oatpp-test"].names["cmake_find_package_multi"] = "oatpp-test"
            self.cpp_info.components["oatpp-test"].set_property("cmake_target_name", "oatpp-test::oatpp-test")
            self.cpp_info.components["oatpp-test"].includedirs = [include_dir]
            self.cpp_info.components["oatpp-test"].libdirs = [lib_dir]
            self.cpp_info.components["oatpp-test"].libs = ["oatpp-test"]
            self.cpp_info.components["oatpp-test"].requires = ["_oatpp"]

        # workaround to have all components in the global target
        self.cpp_info.set_property("cmake_target_name", "oatpp::oatpp-test")
