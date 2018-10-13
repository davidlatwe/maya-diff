

import uuid
import hashlib
import maya.cmds as cmds

try:
    import bson
except ImportError:
    pass

from datetime import datetime


ATTR_ADDRESS = "address"
ATTR_VERIFIER = "verifier"
ATTR_FINGERPRINT = "fingerprint"

Clean = 0
Changed = 1
Duplicated = 2
Untracked = 3


def _get_attr(node, attr):
    """Internal function for attribute getting
    """
    try:
        return cmds.getAttr(node + "." + attr)
    except ValueError:
        return None


def _add_attr(node, attr):
    """Internal function for attribute adding
    """
    try:
        cmds.addAttr(node, longName=attr, dataType="string")
    except RuntimeError:
        # Attribute existed
        pass


def _set_attr(node, attr, value):
    """Internal function for attribute setting
    """
    try:
        cmds.setAttr(node + "." + attr, value, type="string")
    except RuntimeError:
        # Attribute not existed
        pass


def read_address(node):
    """Read address value from node

    Arguments:
        node (str): Maya node name

    """
    return _get_attr(node, ATTR_ADDRESS)


def read_verifier(node):
    """Read verifier value from node

    Arguments:
        node (str): Maya node name

    """
    return _get_attr(node, ATTR_VERIFIER)


def read_fingerprint(node):
    """Read fingerprint value from node

    Arguments:
        node (str): Maya node name

    """
    return _get_attr(node, ATTR_FINGERPRINT)


def read_uuid(node):
    """Read uuid value from node

    Arguments:
        node (str): Maya node name

    """
    muuid = cmds.ls(node, uuid=True)
    if not len(muuid):
        raise RuntimeError("Node not found.")
    elif len(muuid) > 1:
        raise RuntimeError("Found more then one node, use long name.")

    return muuid[0]


def _generate_address():
    """Internal function for generating time-embedded ID address

    Note:
        `bson.ObjectId` is about 1 time faster then `uuid.uuid1`.

    """
    try:
        return str(bson.ObjectId())  # bson is faster
    except NameError:
        return str(uuid.uuid1())[:-18]  # remove mac-addr


def _generate_verifier(muuid, address):
    """Internal function for generating hash value from Maya UUID and address

    Arguments:
        muuid (str): Maya UUID string
        address (str): Previous generated address id from node

    Note:
        Faster then uuid5.

    """
    hasher = hashlib.sha1()
    hasher.update(muuid + ":" + address)
    return hasher.hexdigest()


def is_duplicated(node):
    """Is this node a duplicate ?

    Return True if the `node` is a duplicate, by comparing the `verifier`
    attribute.

    Arguments:
        node (str): Maya node name

    """
    address = read_address(node)
    verifier = read_verifier(node)

    if not all((address, verifier)):
        # Node did not have the attributes for verification,
        # this is new node.
        return True
    else:
        return not verifier == _generate_verifier(read_uuid(node), address)


def is_changed(node, fingerprint):
    """Has this node been modified ?

    Return True if the `node` has been changed, by comparing the `fingerprint`

    Arguments:
        node (str): Maya node name
        fingerprint (str): Maya node's hash value

    """
    origin_fingerprint = read_fingerprint(node)

    if origin_fingerprint is None:
        # Node did not have the attributes for verification,
        # this is new node.
        return True
    else:
        return not fingerprint == origin_fingerprint


def status(node, fingerprint):
    """Report `node` current state

    Return node state flag (int), in range 0 - 3:
        0 == api.Clean
        1 == api.Changed
        2 == api.Duplicated
        3 == api.Untracked

    Arguments:
        node (str): Maya node name
        fingerprint (str): Maya node's hash value

    Returns:
        (int): Node state flag

    """
    return is_changed(node, fingerprint) | (is_duplicated(node) << 1)


def on_track(node, fingerprint):
    """Update node's address and fingerprint

    MUST do this if `status` return flag `api.Untracked`.

    Arguments:
        node (str): Maya node name
        fingerprint (str): Maya node's hash value

    """
    address = _generate_address()
    _add_attr(node, ATTR_ADDRESS)
    _set_attr(node, ATTR_ADDRESS, address)
    on_change(node, fingerprint)
    on_duplicate(node)


def on_change(node, fingerprint):
    """Update node's fingerprint

    MUST do this if `status` return flag `api.Changed`.

    Arguments:
        node (str): Maya node name
        fingerprint (str): Maya node's hash value

    """
    _add_attr(node, ATTR_FINGERPRINT)
    _set_attr(node, ATTR_FINGERPRINT, fingerprint)


def on_duplicate(node, *args):
    """Update node's verifier

    MUST do this if `status` return flag `api.Duplicated`.

    Arguments:
        node (str): Maya node name
        fingerprint (str): Maya node's hash value

    """
    address = read_address(node)
    if address is None:
        return

    verifier = _generate_verifier(read_uuid(node), address)
    _add_attr(node, ATTR_VERIFIER)
    _set_attr(node, ATTR_VERIFIER, verifier)


__action_map = {
    Clean: (lambda n, f: None),
    Changed: on_change,
    Duplicated: on_duplicate,
    Untracked: on_track,
}


def manage(node, fingerprint, state):
    """Auto update node's identity attributes by input state

    Arguments:
        node (str): Maya node name
        fingerprint (str): Maya node's hash value
        state (int): State flag returned from `status`

    """
    action = __action_map[state]
    action(node, fingerprint)


def update_verifiers(nodes):
    """Update input nodes' verifier

    MUST do this on file-import.

    Arguments:
        nodes (list): A list of Maya node name

    """
    for node in nodes:
        on_duplicate(node)


def get_time(node):
    """Retrive datetime object from Maya node

    A little bonus gained from datetime embedded id.

    Arguments:
        node (str): Maya node name

    """
    address = read_address(node)
    if address is None:
        return None

    if "-" in address:
        _ut = uuid.UUID(address + "-0000-000000000000").time
        time = datetime.fromtimestamp((_ut - 0x01b21dd213814000L) * 100 / 1e9)
    else:
        time = bson.ObjectId(address).generation_time

    return time
