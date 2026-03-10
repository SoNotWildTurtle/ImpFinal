import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "communication" / "imp-command-transformer.py"
SPEC = importlib.util.spec_from_file_location("imp_command_transformer", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)
CommandTransformer = module.CommandTransformer





def test_build_and_parse():

    transformer = CommandTransformer()

    msg = transformer.build("ls", {"path": "/tmp"})

    cmd, params = transformer.parse(msg)

    assert cmd == "ls"

    assert params["path"] == "/tmp"





def test_handshake_ack():

    transformer = CommandTransformer()

    info = transformer.handshake("ack")

    assert info["path"][-1] == "bottom->imp"

    verified = transformer.handshake("ack", info["nonce"], info["digest"])

    assert verified["digest"] == info["digest"]





def test_unknown_command():

    transformer = CommandTransformer()

    try:
        transformer.build("invalid")
    except ValueError:
        return
    raise AssertionError("Expected ValueError for invalid command")

