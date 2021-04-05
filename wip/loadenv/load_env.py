#!/usr/bin/env python3

"""
TODO:

    * Create routine to load EnvKeywordParser.
    * Create routine to load SetEnvironment.
    * Add --list-envs feature.
    * Ensure we apply() the environment before writing load_matching_env.sh so
      SetEnvironment ensures the environment is valid first.
    * Increase test coverage.
    * Ensure load-env.ini is well-formed.

"""

import argparse
from configparserenhanced import ConfigParserEnhanced
from pathlib import Path
import re
from setenvironment import SetEnvironment
from src.env_keyword_parser import EnvKeywordParser
from src.load_env_common import LoadEnvCommon
import socket
import sys
import textwrap


class LoadEnv(LoadEnvCommon):
    """
    Insert description here.

    Attributes:
        argv:  The command line arguments passed to ``load_env.sh``.
    """

    def parse_top_level_config_file(self):
        """
        Parse the ``load-env.ini`` file and store the corresponding
        ``configparserenhanceddata`` object as :attr:`load_env_config_data`.
        """
        if self.load_env_config_data is None:
            self.load_env_config_data = ConfigParserEnhanced(
                self._load_env_ini_file
            ).configparserenhanceddata

    def parse_supported_systems_file(self):
        """
        Parse the ``supported-systems.ini`` file and store the corresponding
        ``configparserenhanceddata`` object as :attr:`supported_systems_data`.
        """
        if self.supported_systems_data is None:
            self.supported_systems_data = ConfigParserEnhanced(
                self.args.supported_systems_file
            ).configparserenhanceddata

    def __init__(
        self, argv, load_env_ini="load_env.ini"
    ):
        if not isinstance(argv, list):
            raise TypeError("LoadEnv must be instantiated with a list of "
                            "command line arguments.")
        self.argv = argv
        self._load_env_ini_file = load_env_ini
        self.load_env_config_data = None
        self.parse_top_level_config_file()
        self.supported_systems_data = None
        self.parse_supported_systems_file()
        self.system_name = None

    def get_sys_name_from_hostname(self, hostname):
        """
        Helper function to match the given hostname to a system name, as
        defined by the ``supported-systems.ini``.  If nothing is matched,
        ``None`` is returned.

        Parameters:
            hostname (str):  The hostname to match a system name to.

        Returns:
            str:  The matched system name, or ``None`` if nothing is matched.
        """
        sys_names = [s for s in self.supported_systems_data.sections()
                     if s != "DEFAULT"]
        sys_name_from_hostname = None
        for sys_name in sys_names:
            # Strip the keys of comments:
            #
            #   Don't match anything following whitespace and a '#'.
            #                                  |
            #   Match anything that's not      |
            #        a '#' or whitespace.      |
            #                      vvvvv    vvvvvvvv
            keys = [re.findall(r"([^#^\s]*)(?:\s*#.*)?", key)[0]
                    for key in self.supported_systems_data[sys_name].keys()]

            # Keys are treated as REGEXes.
            matches = []
            for key in keys:
                matches += re.findall(key, hostname)
            if len(matches) > 0:
                sys_name_from_hostname = sys_name
                break
        return sys_name_from_hostname

    def get_sys_name_from_build_name(self):
        """
        Helper function that finds any system name in ``supported-systems.ini``
        that exists in the ``build_name``.  If more than one system name is
        matched, an exception is raised, and if no system names are matched,
        then ``None`` is returned.

        Returns:
            str:  The matched system name in the build name, if it exists. If
            not, return ``None``.
        """
        sys_names = [s for s in self.supported_systems_data.sections()
                     if s != "DEFAULT"]
        sys_name_from_build_names = [_ for _ in sys_names if _ in
                                     self.args.build_name]
        if len(sys_name_from_build_names) > 1:
            msg = self.get_msg_for_list(
                "Cannot specify more than one system name in the build name\n"
                "You specified", sys_name_from_build_names
            )
            sys.exit(msg)
        elif len(sys_name_from_build_names) == 0:
            sys_name_from_build_name = None
        else:
            sys_name_from_build_name = sys_name_from_build_names[0]
        return sys_name_from_build_name

    def determine_system(self):
        """
        Determine which system from ``supported-envs.ini`` to use, either by
        grabbing what's specified in the :attr:`build_name`, or by using the
        hostname and ``supported-systems.ini``.  Store the result as
        :attr:`system_name`.
        """
        if self.system_name is None:
            hostname = socket.gethostname()
            sys_name_from_hostname = self.get_sys_name_from_hostname(hostname)
            self.system_name = sys_name_from_hostname
            sys_name_from_build_name = self.get_sys_name_from_build_name()
            if (sys_name_from_hostname is None and
                    sys_name_from_build_name is None):
                msg = self.get_formatted_msg(
                    f"Unable to find valid system name in the build name or "
                    f"for the hostname '{hostname}'\n in "
                    f"'{self.args.supported_systems_file}'."
                )
                sys.exit(msg)

            # Use the system name in build_name if sys_name_from_hostname is
            # None.
            if sys_name_from_build_name is not None:
                self.system_name = sys_name_from_build_name
                if (sys_name_from_hostname is not None
                        and sys_name_from_hostname != self.system_name
                        and self.args.force is False):
                    msg = self.get_formatted_msg(
                        f"Hostname '{hostname}' matched to system "
                        f"'{sys_name_from_hostname}'\n in "
                        f"'{self.args.supported_systems_file}', but you "
                        f"specified '{self.system_name}' in the build name.\n"
                        "If you want to force the use of "
                        f"'{self.system_name}', add the --force flag."
                    )
                    sys.exit(msg)

    @property
    def parsed_env_name(self):
        """
        This property instantiates an :class:`EnvKeywordParser` object with
        this object's :attr:`build_name`, :attr:`system_name`, and
        ``supported-envs.ini``. From this object, the qualified environment
        name is retrieved and returned.

        Returns:
            str:  The qualified environment name from parsing the
            :attr:`build_name`.
        """
        if not hasattr(self, "_parsed_env_name"):
            self.determine_system()
            ekp = EnvKeywordParser(self.args.build_name, self.system_name,
                                   self.args.supported_envs_file)
            self._parsed_env_name = ekp.qualified_env_name
        return self._parsed_env_name

    def write_load_matching_env(self):
        """
        Write a bash script that when sourced will give you the same
        environment loaded by this tool.

        Returns:
            Path:  The path to the script that was written, either the default,
            or whatever the user requested with ``--output``.
        """
        se = SetEnvironment(filename=self.args.environment_specs_file)
        files = [Path("/tmp/load_matching_env.sh").resolve()]
        if self.args.output:
            files += [self.args.output]
        for f in files:
            if f.exists():
                f.unlink()
            f.parent.mkdir(parents=True, exist_ok=True)
            se.write_actions_to_file(f, self.parsed_env_name,
                                     include_header=True, interpreter="bash")
        return files[-1]

    def get_valid_file_path(self, args_path, flag):
        """
        Check to see if the path specified for a given configuration file is
        valid.  If not, try to grab it from the ``load-env.ini`` file.

        Parameters:
            args_path (Path, None):  A path from :attr:`args`.
            flag (str):  The corresponding flag in both the ``load-env.ini``
                file and on the command line.

        Throws:
            ValueError:  If the ``load-env.ini`` file doesn't specify a path to
                the given configuration file.

        Returns:
            Path:  The valid path to the configuration file.
        """
        file_path = args_path
        if file_path is None:
            file_path = self.load_env_config_data["load-env"][flag]
        if file_path == "" or file_path is None:
            msg = (f"You must specify a path to the `{flag}.ini` file either "
                   f"in the `load-env.ini` file or via `--{flag}` on the "
                   "command line.")
            raise ValueError(self.get_formatted_msg(msg))
        file_path = Path(file_path).resolve()
        return file_path

    @property
    def args(self):
        """
        The parsed command line arguments to the script.

        Returns:
            argparse.Namespace:  The parsed arguments.
        """
        if not hasattr(self, "_args"):
            args = self.__parser().parse_args(self.argv)
            args.supported_systems_file = self.get_valid_file_path(
                args.supported_systems_file,
                "supported-systems"
            )
            args.supported_envs_file = self.get_valid_file_path(
                args.supported_envs_file,
                "supported-envs"
            )
            args.environment_specs_file = self.get_valid_file_path(
                args.environment_specs_file,
                "environment-specs"
            )
            self._args = args
        return self._args

    def __parser(self):
        """
        Returns:
            argparse.ArgumentParser:  The parser bject with properly configured
            argument options.  This is to be used in conjunction with
            :attr:`args`.
        """
        if hasattr(self, "_parser"):
            return self._parser

        description = "[ Load Environment Utility ]".center(79, "-")

        examples = """
            Basic Usage::

                load_env.sh build_name-here
        """
        examples = textwrap.dedent(examples)
        examples = "[ Examples ]".center(79, "-") + "\n\n" + examples

        parser = argparse.ArgumentParser(
            description=description,
            epilog=examples,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        parser.add_argument("build_name", help="The keyword string for which "
                            "you wish to load the environment.")

        parser.add_argument("-o", "--output", action="store", default=None,
                            type=lambda p: Path(p).resolve(), help="Output a "
                            "bash script that when sourced will give you an "
                            "environment identical to the one loaded when "
                            "using this tool.")

        parser.add_argument("-f", "--force", action="store_true",
                            default=False, help="Forces load_env to use the "
                            "system name specified in the build_name rather "
                            "than the system name matched via the hostname "
                            "and the supported-systems.ini file.")

        config_files = parser.add_argument_group(
            "configuration file overrides"
        )
        config_files.add_argument("--supported-systems",
                                  dest="supported_systems_file",
                                  action="store", default=None,
                                  type=lambda p: Path(p).resolve(),
                                  help="Path to ``supported-systems.ini``.  "
                                  "Overrides loading the file specified in "
                                  "``load_env.ini``.")
        config_files.add_argument("--supported-envs", default=None,
                                  dest="supported_envs_file", action="store",
                                  type=lambda p: Path(p).resolve(),
                                  help="Path to ``supported-envs.ini``.  "
                                  "Overrides loading the file specified in "
                                  "``load_env.ini``.")
        config_files.add_argument("--environment-specs",
                                  dest="environment_specs_file",
                                  action="store", default=None,
                                  type=lambda p: Path(p).resolve(),
                                  help="Path to ``environment-specs.ini``.  "
                                  "Overrides loading the file specified in "
                                  "``load_env.ini``.")

        return parser


def main(argv):
    """
    DOCSTRING
    """
    le = LoadEnv(argv)
    le.write_load_matching_env()
    le.determine_system()


if __name__ == "__main__":
    main(sys.argv[1:])
