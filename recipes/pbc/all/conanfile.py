from conans import ConanFile, AutoToolsBuildEnvironment, tools
from six import StringIO
import os

required_conan_version = ">=1.33.0"

class PbcConan(ConanFile):
    name = "pbc"
    version = "0.5.14"
    topics = ("pbc", "crypto", "cryptography", "security", "pairings" "cryptographic")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://crypto.stanford.edu/pbc/"
    license = "LGPL-3.0"
    description = "The PBC (Pairing-Based Crypto) library is a C library providing low-level routines for pairing-based cryptosystems."

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    _autotools = None
    exports_sources = "patches/**"

    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd

    def requirements(self):
        self.requires("gmp/6.2.1")

    def build_requirements(self):
        self.build_requires("bison/3.7.6")
        self.build_requires("flex/2.6.4")

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def source(self):
        tools.get(**self.conan_data["sources"][self.version], strip_root=True)

    # Helper to run a command and return the output as a stripped string
    def run_get_output(self, *args):
        buf = StringIO()
        self.run(args, output=buf)
        return buf.getvalue().strip()

    def _configure_autotools(self):
        if self._autotools:
            return self._autotools
        self._autotools = AutoToolsBuildEnvironment(self, win_bash=tools.os_info.is_windows)
        # Need to override environment or configure will fail despite that flex
        # is actually available.
        args = ["LEX=flex"]
        if self.options.shared:
            args.extend(["--disable-static", "--enable-shared"])
        else:
            args.extend(["--disable-shared", "--enable-static"])

        # No idea why this is necessary, but if you don't set CC this way, then
        # configure complains that it can't find gmp.
        if self.settings.os == "iOS":
            if self.settings.arch == "x86_64":
                platform = "iphonesimulator"
                target = "x86_64-apple-darwin"
            else:
                platform = "iphoneos"
                target = "arm64-apple-darwin"
            sdk_path = self.run_get_output(
                "xcrun", "-sdk", platform, "-show-sdk-path")
            cc = self.run_get_output("xcrun", "-sdk", platform, "-find", "cc")
            min_ios = "-miphoneos-version-min={}".format(
                self.settings.os.version)
            args.append("CC={} -isysroot {} -target {} {}".format(
                cc, sdk_path, target, min_ios))

        self._autotools.configure(args=args)
        return self._autotools

    def build(self):
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            tools.patch(**patch)
        autotools = self._configure_autotools()
        autotools.make()

    def package(self):
        self.copy(pattern="COPYING", dst="licenses")
        autotools = self._configure_autotools()
        autotools.install()
        tools.rmdir(os.path.join(self.package_folder, "share"))
        tools.remove_files_by_mask(os.path.join(self.package_folder, "lib"), "*.la")

    def package_info(self):
        self.cpp_info.libs = ["pbc"]
