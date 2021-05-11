from configparserenhanced import ConfigParserEnhanced
from pathlib import Path
import re
from src.gen_config_commong import GenConfigCommon
import sys
import textwrap


class ConfigKeywordParser(GenConfigCommon, KeywordParser):
    """
    This class accepts a configuration file containing supported environments
    on various machines in the following format::

        [machine-type-5]
        intel-18.0.5-mpich-7.7.6:   # Environment name 1
            intel-18    # Alias 1 for ^^^
            intel       # Alias 2 for ^^^
            default-env # ...
        intel-19.0.4-mpich-7.7.6:   # Environment name 2
            intel-19

        [machine-name-2]
        use machine-type-5  # As if contents of machine-type-5 are copy-pasted here

        [sys-3]
        ...

    Usage::

        ekp = EnvKeywordParser("intel-18", "machine-type-5", "supported_envs.ini")
        qualified_env_name = ekp.qualified_env_name

    Parameters:
        build_name (str):  Keyword string to parse environment name from.
        system_name (str):  The name of the system this script is being run
            on.
        supported_envs_filename (str, Path):  The name of the file to load
            the supported environment configuration from.
    """

    def __init__(self, build_name, system_name, supported_envs_filename):
        self._supported_envs = None
        self.supported_envs_filename = supported_envs_filename
        self.build_name = build_name.replace("_", "-")
        self.system_name = system_name

        env_names = [_ for _ in self.supported_envs[self.system_name].keys()]
        self.env_names = sorted(env_names, key=len, reverse=True)
        self.aliases = sorted(self.get_aliases(), key=len, reverse=True)

    @property
    def supported_envs(self):
        """
        Gets the :class:`ConfigParserEnhancedData` object with
        :attr:`supported_envs_filename` loaded.

        Returns:
            ConfigParserEnhancedData:  A :class:`ConfigParserEnhancedData`
            object with `supported_envs_filename` loaded.
        """
        self._supported_envs = ConfigParserEnhanced(
            self.supported_envs_filename
        ).configparserenhanceddata
        return self._supported_envs

    @property
    def qualified_env_name(self):
        """
        Parses the :attr:`build_name` and returns the fully qualified
        environment name that is listed as supported for the current
        :attr:`system_name` in the file :attr:`supported_envs_filename`.
        The way this happens is:

            * Gather the list of environment names, sorting them from longest
              to shortest.

                 * March through this list, checking if any of these appear in
                   the :attr:`build_name`.
                 * If an environment name is matched, continue past alias
                   checking.
                 * If not, move on to aliases.

            * Gather the list of aliases, sorting them from longest to
              shortest.

                 * March through this list, checking if any of these appear in
                   the :attr:`build_name`.
                 * Get the environment name with
                   :func:`get_env_name_for_alias`.

            * Run
              :func:`assert_kw_str_versions_for_env_name_components_are_supported`
              to make sure component versions specified in the
              :attr:`build_name` are supported.
            * Run :func:`assert_kw_str_node_type_is_supported` to make sure the
              node type (``serial`` or ``openmp``) specified in the
              :attr:`build_name` is supported on the system.
            * Done

        Returns:
            str:  The fully qualified environment name.
        """
        if not hasattr(self, "_qualified_env_name"):
            matched_env_name = None
            for name in self.env_names:
                if name in self.build_name:
                    matched_env_name = name
                    print(f"Matched environment name '{name}' in build name "
                          f"'{self.build_name}'.")
                    break

            if matched_env_name is None:
                matched_alias = None
                for alias in self.aliases:
                    if alias in self.build_name:
                        matched_alias = alias
                        break

                if matched_alias is None:
                    msg = self.get_msg_showing_supported_environments(
                        "Unable to find alias or environment name for system "
                        f"'{self.system_name}' in\nkeyword string "
                        f"'{self.build_name}'."
                    )
                    sys.exit(msg)

                matched_env_name = self.get_env_name_for_alias(matched_alias)
                print(f"NOTICE:  Matched alias '{matched_alias}' in build "
                      f"name '{self.build_name}' to environment name "
                      f"'{matched_env_name}'.")

            self.assert_kw_str_versions_for_env_name_components_are_supported(
                matched_env_name
            )
            self.assert_kw_str_node_type_is_supported(matched_env_name)

            self._qualified_env_name = f"{self.system_name}-{matched_env_name}"

        return self._qualified_env_name

    def get_aliases(self):
        """
        Gets the aliases for the current :attr:`system_name` and returns them
        in list form. This also runs
        :func:`assert_alias_list_values_are_unique` and
        :func:`assert_aliases_not_equal_to_env_names` on the alias list.

        Returns:
            list:  The filtered and validated list of aliases for the current
            :attr:`system_name`.
        """
        # e.g. aliases = ['\ngnu  # GNU\ndefault-env # The default',
        #                 '\ncuda-gnu\ncuda']
        aliases = []
        for env_name in self.supported_envs[self.system_name].keys():
            aliases += self.get_values_for_section_key(self.system_name,
                                                       env_name)

        self.assert_alias_list_values_are_unique(aliases)
        self.assert_aliases_not_equal_to_env_names(aliases)

        return aliases

# TODO: Pull this out and rename to something like get_key_for_value_substring
#       - i.e. value_substring in configparser[section_name][matched_key],
#         which could be something like f"\ngnu\n  {value_substring}\n"
    def get_env_name_for_alias(self, matched_alias):
        """
        Returns the environment name for which the alias specifies. For
        example, ``matched_alias = intel`` would return
        ``intel-18.0.5-mpich-7.7.6`` for the follwing configuration::

            [machine-type-5]
            intel-18.0.5-mpich-7.7.6:
                intel-18
                intel
                default-env
            intel-19.0.4-mpich-7.7.6:
                intel-19

        Parameters:
            matched_alias (str):  The alias to find the environment name for.

        Returns:
            str:  The environment name for the alias.
        """
        unsorted_env_names = [_ for _ in
                              self.supported_envs[self.system_name].keys()]

        unparsed_aliases = [_ for _ in
                            self.supported_envs[self.system_name].values()]

        matched_index = None
        for idx, a in enumerate(unparsed_aliases):
            if a is None or a == "":
                continue

            # The following regex is explained in :func:`get_aliases`.
            uncommented_alias_list = re.findall(
                r"(?:\s*?#.*\n*)*([^#^\n]*)", a
            )
            aliases_for_env = [_.strip().replace("_", "-")
                               for _ in uncommented_alias_list if _ != ""]
            if matched_alias in aliases_for_env:
                matched_index = idx
                break

        if matched_index is None:
            msg = self.get_formatted_msg("Unable to find alias "
                                         f"'{matched_alias}' in aliases "
                                         f"for '{self.system_name}'.\n")
            sys.exit(msg)

        matched_env_name = unsorted_env_names[matched_index]

        return matched_env_name

# TODO: This can be generalized for both EnvKeywordParser and
#       ConfigKeywordParser. Add swapping of 'Environments', 'Aliases', and the
#       .ini file to see for details
    def get_msg_showing_supported_environments(self, msg, kind="ERROR"):
        """
        Similar to :func:`get_msg_for_list`, except it's a bit more specific.
        Produces an error message like::

            +=================================================================+
            |   {kind}:  {msg}
            |
            |   - Supported Environments for 'machine-type-5':
            |     - intel-18.0.5-mpich-7.7.6
            |       * Aliases:
            |         - intel-18
            |         - intel
            |         - default-env
            |     - intel-19.0.4-mpich-7.7.6
            |       * Aliases:
            |         - intel-19
            |   See {self.supported_envs_filename} for details.
            +=================================================================+

        Parameters:
            msg (str):  The main error message to be displayed.  Can be
                multiline.
            kind (str):  The kind of message being generated, e.g., "ERROR",

                "WARNING", "INFO", etc.

        Returns:
            str:  The formatted message.
        """
        extras = f"\n- Supported Environments for '{self.system_name}':\n"
        for name in sorted(self.env_names):
            extras += f"  - {name}\n"
            aliases_for_env = sorted(
                [a for a in self.aliases
                 if self.get_env_name_for_alias(a) == name]
            )
            extras += ("    * Aliases:\n" if len(aliases_for_env) > 0 else "")
            for a in aliases_for_env:
                extras += (f"      - {a}\n")
        extras += f"\nSee {self.supported_envs_filename} for details."
        msg = self.get_formatted_msg(msg, kind=kind, extras=extras)
        return msg

    def assert_alias_list_values_are_unique(self, alias_list):
        """
        Ensures we don't run into a situation like::

            [machine-type-5]
            intel-18.0.5-mpich-7.7.6:
                intel-18
                intel
                default-env
            intel-19.0.4-mpich-7.7.6:
                intel-19
                intel     # Duplicate of 'intel' in the above section!

        Called automatically by :func:`get_aliases`.

        Parameters:
            alias_list (str): A list of aliases to check for duplicates.
        """
        duplicates = [_ for _ in set(alias_list) if alias_list.count(_) > 1]
        try:
            assert duplicates == []
        except AssertionError:
            msg = self.get_msg_for_list(
                f"Aliases for '{self.system_name}' contains duplicates:",
                duplicates
            )
            sys.exit(msg)

    def assert_aliases_not_equal_to_env_names(self, alias_list):
        """
        Ensures we don't run into a situation like::

            [machine-type-5]
            intel-18.0.5-mpich-7.7.6:
                intel-18
                intel
                default-env
            intel-19.0.4-mpich-7.7.6:
                intel-19
                intel-18.0.5-mpich-7.7.6  # Same as the other environment name!

        Called automatically by :func:`get_aliases`.

        Parameters:
            alias_list (str): A list of aliases to check for environemnt names.

        Raises:
            SystemExit:  If the user requests an unsupported version.
        """
        duplicates = [_ for _ in alias_list if _ in self.env_names]
        try:
            assert duplicates == []
        except AssertionError:
            msg = self.get_msg_for_list(
                f"Alias found for '{self.system_name}' that matches an "
                "environment name:", duplicates
            )
            sys.exit(msg)
