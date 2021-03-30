from pathlib import Path
import pytest
import re
import sys

root_dir = (Path.cwd()/".."
            if (Path.cwd()/"conftest.py").exists()
            else Path.cwd())
sys.path.append(str(root_dir))
from src.env_keyword_parser import EnvKeywordParser


def test_supported_envs_ini_is_read_correctly():
    ekp = EnvKeywordParser("default-env", "machine-type-1", "test_supported_envs.ini")
    se = ekp.supported_envs
    assert se is not None

    # Structure Checks
    """
    e.g.
        [machine-type-1]
        intel-18.0.5-mpich-7.7.6:   << se["machine-type-1"].keys()
            intel-18             <-|
            intel                  |-< se["machine-type-1"].values()
            default-env          <-|
        intel-19.0.4-mpich-7.7.6:   << se["machine-type-1"].keys()
            intel-19                << se["machine-type-1"].values()
    """
    assert [_ for _ in se.keys()] != ["DEFAULT"]
    assert [_ for _ in se["machine-type-1"].keys()] != []
    assert "default-env" in "\n".join([_ for _ in se["machine-type-1"].values()])


def test_invalid_supported_envs_filename_raises():
    with pytest.raises(IOError) as excinfo:
        ekp = EnvKeywordParser("", "machine-type-1", "invalid_filename_here.ini")
        ekp.supported_envs
    exception_message = excinfo.value.args[0]
    assert ("ERROR: Unable to load configuration .ini file" in
            exception_message)


#####################
#  Keyword Parsing  #
#####################
@pytest.mark.parametrize("keyword", [
    {
        "str": "machine-type-1-intel-19.0.4_mpich-7.7.15_hsw_openmp_static_dbg",
        "qualified_env_name": "machine-type-1-intel-19.0.4-mpich-7.7.15-hsw-openmp",
        "system_name": "machine-type-1",
    },
    {
        "str": "default-env-knl",
        "qualified_env_name": "machine-type-1-intel-19.0.4-mpich-7.7.15-knl-openmp",
        "system_name": "machine-type-1",
    },
    {
        "str": "intel_hsw",
        "qualified_env_name": "machine-type-1-intel-19.0.4-mpich-7.7.15-hsw-openmp",
        "system_name": "machine-type-1",
    },
    {
        "str": "machine-type-4-arm-20.1",
        "qualified_env_name": "machine-type-4-arm-20.1-openmpi-4.0.3-openmp",
        "system_name": "machine-type-4",
    },
    {
        "str": "arm-serial",
        "qualified_env_name": "machine-type-4-arm-20.0-openmpi-4.0.2-serial",
        "system_name": "machine-type-4",
    },
])
def test_keyword_parser_matches_correctly(keyword):
    ekp = EnvKeywordParser(keyword["str"], keyword["system_name"],
                           "test_supported_envs.ini")
    assert ekp.qualified_env_name == keyword["qualified_env_name"]


@pytest.mark.parametrize("kw_str", ["intel-19.0.4-mpich-7.7.15-hsw-openmp",
                                    "intel_19.0.4_mpich_7.7.15-hsw-openmp"])
def test_underscores_hyphens_dont_matter_for_kw_str(kw_str):
    ekp = EnvKeywordParser(kw_str, "machine-type-1", "test_supported_envs.ini")
    assert ekp.qualified_env_name == "machine-type-1-intel-19.0.4-mpich-7.7.15-hsw-openmp"


def test_nonexistent_env_name_or_alias_raises():
    ekp = EnvKeywordParser("bad_kw_str", "machine-type-1", "test_supported_envs.ini")

    with pytest.raises(SystemExit) as excinfo:
        ekp.qualified_env_name
    exc_msg = excinfo.value.args[0]

    assert ("ERROR:  Unable to find alias or environment name for system "
            "'machine-type-1' in") in exc_msg
    assert "keyword string 'bad-kw-str'" in exc_msg


@pytest.mark.parametrize("inputs", [
    {"system_name": "machine-type-1",
     "build_name": "intel-19.0.4-mpich-7.7.15-hsw-openmp",
     "matched_env_name": "intel-19.0.4-mpich-7.7.15-hsw-openmp",
     "versioned_components": ["intel-19.0.4", "mpich-7.7.15", "hsw",
                              "openmp"]},
    {"system_name": "machine-type-4",
     "build_name": "arm-20.0-openmpi-4.0.2-openmp",
     "matched_env_name": "arm-20.0-openmpi-4.0.2-openmp",
     "versioned_components": ["arm-20.0", "openmpi-4.0.2", "openmp"]},
    {"system_name": "machine-type-4",
     "build_name": "arm-serial",
     "matched_env_name": "arm-20.0-openmpi-4.0.2-serial",
     "versioned_components": ["arm", "serial"]},
    {"system_name": "machine-type-4",
     "build_name": "arm-20.0-serial",
     "matched_env_name": "arm-20.0-openmpi-4.0.2-serial",
     "versioned_components": ["arm-20.0", "serial"]}
])
def test_versioned_components_determined_correctly(inputs):
    ekp = EnvKeywordParser(inputs["build_name"], inputs["system_name"],
                           "test_supported_envs.ini")
    ekp.qualified_env_name
    versioned_components = ekp.get_versioned_components_from_str(
        inputs["matched_env_name"], inputs["build_name"]
    )
    assert versioned_components == inputs["versioned_components"]


@pytest.mark.parametrize("inputs", [
    {"system_name": "machine-type-1", "build_name": "intel-20",
     "unsupported_components": ["intel-20"]},
    {"system_name": "machine-type-1", "build_name": "intel-19-mpich-7.2",
     "unsupported_components": ["intel-19", "mpich-7.2"]},
    {"system_name": "machine-type-4", "build_name": "arm-20.2",
     "unsupported_components": ["arm-20.2"]},
    {"system_name": "machine-type-4", "build_name": "arm-20.1-openmpi-4.0.2",
     "unsupported_components": ["arm-20.1", "openmpi-4.0.2"]},
    {"system_name": "machine-type-1",
     "build_name": "intel-20.0.4-mpich-8.7.15-hsw-1.2.3-openmp-4.5.6",
     "unsupported_components": ["intel-20.0.4", "mpich-8.7.15", "hsw-1.2.3",
                                "openmp-4.5.6"]}
])
def test_unsupported_versions_are_rejected(inputs):
    ekp = EnvKeywordParser(inputs["build_name"], inputs["system_name"],
                           "test_supported_envs.ini")

    with pytest.raises(SystemExit) as excinfo:
        ekp.qualified_env_name
    exc_msg = excinfo.value.args[0]

    msgs_expected = []
    if len(inputs["unsupported_components"]) == 1:
        msgs_expected += [(f"ERROR:  '{inputs['unsupported_components'][0]}' "
                           "is not supported")]
    elif len(inputs["unsupported_components"]) == 2:
        msgs_expected += [(f"ERROR:  '{inputs['unsupported_components'][0]}' "
                           f"and '{inputs['unsupported_components'][1]}' are "
                           "not supported together")]
    else:
        msgs_expected += [(f"ERROR:  '{inputs['unsupported_components'][0]}', "
                           f"'{inputs['unsupported_components'][1]}', "),
                           "are not supported together"]
    for msg in msgs_expected:
        msg = msg.replace(" ", r"\s+\|?\s*") # account for line breaks
        assert re.search(msg, exc_msg) is not None

    if inputs["system_name"] == "machine-type-1":
        assert "intel-19.0.4-mpich-7.7.15-hsw-openmp" in exc_msg
        assert "- intel-hsw-openmp\n" in exc_msg
        assert "- intel-hsw\n" in exc_msg
        assert "- intel-openmp\n" in exc_msg
        assert "- intel\n" in exc_msg
        assert "- default-env-hsw\n" in exc_msg
        assert "intel-19.0.4-mpich-7.7.15-knl-openmp" in exc_msg
        assert "- intel-knl-openmp\n" in exc_msg
        assert "- intel-knl\n" in exc_msg
        assert "- default-env-knl\n" in exc_msg
    else:
        assert "arm-20.0-openmpi-4.0.2-openmp" in exc_msg
        assert "arm-20.0-openmpi-4.0.2-serial" in exc_msg
        assert "arm-20.1-openmpi-4.0.3-openmp" in exc_msg
        assert "arm-20.1-openmpi-4.0.3-serial" in exc_msg


@pytest.mark.parametrize("inputs", [
    {"system_name": "machine-type-1", "build_name": "intel-hsw-serial",
     "unsupported_component": "serial"},
    {"system_name": "machine-type-1", "build_name": "intel-serial",
     "unsupported_component": "serial"},
    {"system_name": "test-system", "build_name": "env-name-openmp",
     "unsupported_component": "openmp"},
    {"system_name": "ride", "build_name": "cuda-serial",
     "unsupported_component": "static"},
    {"system_name": "ride", "build_name": "cuda-10-openmp",
     "unsupported_component": "openmp"},
])
def test_unsupported_node_types_are_rejected(inputs):
    ekp = EnvKeywordParser(inputs["build_name"], inputs["system_name"],
                           "test_supported_envs.ini")

    with pytest.raises(SystemExit) as excinfo:
        ekp.qualified_env_name
    exc_msg = excinfo.value.args[0]

    if inputs["system_name"] == "ride":
        assert ("ERROR:  The 'serial' and 'openmp' node types are not "
                "applicable to CUDA") in exc_msg
    else:
        assert (f"ERROR:  '{inputs['unsupported_component']}' was specified "
                "in the build name, but only") in exc_msg

    if inputs["system_name"] == "machine-type-1":
        assert "intel-19.0.4-mpich-7.7.15-hsw-openmp" in exc_msg
        assert "- intel-hsw-openmp\n" in exc_msg
        assert "- intel-hsw\n" in exc_msg
        assert "- intel-openmp\n" in exc_msg
        assert "- intel\n" in exc_msg
        assert "- default-env-hsw\n" in exc_msg
        assert "intel-19.0.4-mpich-7.7.15-knl-openmp" in exc_msg
        assert "- intel-knl-openmp\n" in exc_msg
        assert "- intel-knl\n" in exc_msg
        assert "- default-env-knl\n" in exc_msg
    elif inputs["system_name"] == "ride":
        assert "cuda-9.2-gnu-7.2.0-openmpi-2.1.2" in exc_msg
        assert "- cuda-9" in exc_msg
        assert "- cuda" in exc_msg
    elif inputs["system_name"] == "machine-type-4":
        assert "env-name-serial" in exc_msg
        assert "- env-name" in exc_msg


#############
#  Aliases  #
#############
def test_underscores_hyphens_dont_matter_for_aliases():
    # "intel-18" and "intel_default" are aliases for "machine-type-1"
    ekp = EnvKeywordParser("intel-18", "machine-type-1", "test_supported_envs.ini")
    aliases = ekp.get_aliases()
    assert "intel-hsw" in aliases
    assert "intel_hsw" not in aliases  # Even though this is how it's
    #                                    defined in the .ini


@pytest.mark.parametrize("bad_alias", [
    {
        "alias": "intel",
        "err_msg": "ERROR:  Aliases for 'machine-type-1' contains duplicates:",
    },
    {
        "alias": "intel-18.0.5-mpich-7.7.15",
        "err_msg": ("ERROR:  Alias found for 'machine-type-1' that matches an environment"
                    " name:"),
    },
    {
        "alias": "intel-19.0.4-mpich-7.7.15",
        "err_msg": ("ERROR:  Alias found for 'machine-type-1' that matches an environment"
                    " name:"),
    },
])
def test_alias_values_are_unique(bad_alias):
    bad_supported_envs = (
        "[machine-type-1]\n"
        "intel-18.0.5-mpich-7.7.15: # Comment here\n"
        "    intel-18              # Comment here\n"
        "    intel                 # Comment here too\n"
        "    default-env           # It's the default\n"
        "intel-19.0.4-mpich-7.7.15:\n"
        "    intel-19\n"
        f"    {bad_alias['alias']}\n"
    )
    filename = "bad_supported_envs.ini"
    with open(filename, "w") as f:
        f.write(bad_supported_envs)

    with pytest.raises(SystemExit) as excinfo:
        EnvKeywordParser("default-env", "machine-type-1", filename)
    exc_msg = excinfo.value.args[0]

    assert bad_alias["err_msg"] in exc_msg
    assert f"- {bad_alias['alias']}\n" in exc_msg


@pytest.mark.parametrize("multiple_aliases", [True, False])
def test_alias_values_do_not_contain_whitespace(multiple_aliases):
    bad_supported_envs = (
        "[machine-type-1]\n"
        "intel-18.0.5-mpich-7.7.15: # Comment here\n"
        "    intel 18              # Space in this alias\n" +
        ("    intel default\n" if multiple_aliases is True else "") +
        "    intel                 # Comment here too\n"
    )
    filename = "bad_supported_envs.ini"
    with open(filename, "w") as f:
        f.write(bad_supported_envs)

    with pytest.raises(SystemExit) as excinfo:
        EnvKeywordParser("intel-18", "machine-type-1", filename)
    exc_msg = excinfo.value.args[0]

    es = "es" if multiple_aliases is True else ""
    s = "" if multiple_aliases is True else "s"
    assert f"The following alias{es} contain{s} whitespace:" in exc_msg
    assert "- intel 18\n" in exc_msg
    if multiple_aliases is True:
        assert "- intel default\n" in exc_msg


@pytest.mark.parametrize("general_section_order", ["first", "last"])
def test_general_alias_matches_correct_env_name(general_section_order):
    general_section = (
        "intel-18.0.5-mpich-7.7.15: # Comment here\n"
        "    intel-18              # Comment here\n"
        "    intel                 # This is the general alias\n"
        "    default-env           # It's the default"
    )
    other_section = (
        "intel-19.0.4-mpich-7.7.15:\n"
        "    intel-19"
    )
    supported_envs = "\n".join([
        "[machine-type-1]",
        general_section if general_section_order == "first" else other_section,
        other_section if general_section_order == "first" else general_section,
    ])

    filename = "test_general_alias_supported_envs.ini"
    with open(filename, "w") as f:
        f.write(supported_envs)

    ekp = EnvKeywordParser("intel", "machine-type-1", filename)
    assert ekp.get_env_name_for_alias("intel") == "intel-18.0.5-mpich-7.7.15"


def test_matched_alias_not_in_supported_envs_raises():
    ekp = EnvKeywordParser("intel", "machine-type-1", "test_supported_envs.ini")

    with pytest.raises(SystemExit) as excinfo:
        ekp.get_env_name_for_alias("bad_alias")
    exc_msg = excinfo.value.args[0]

    assert ("ERROR:  Unable to find alias 'bad_alias' in aliases for "
            "'machine-type-1'") in exc_msg
