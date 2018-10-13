

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


def _get_attr(node, attr):
    """
    """
    try:
        return cmds.getAttr(node + "." + attr)
    except ValueError:
        return None


def _add_attr(node, attr):
    """
    """
    try:
        cmds.addAttr(node, longName=attr, dataType="string")
    except RuntimeError:
        # Attribute existed
        return False
    else:
        return True


def _set_attr(node, attr, value):
    """
    """
    try:
        cmds.setAttr(node + "." + attr, value, type="string")
    except RuntimeError:
        # Attribute existed
        return False
    else:
        return True


def read_address(node):
    """
    """
    return _get_attr(node, ATTR_ADDRESS)


def read_verifier(node):
    """
    """
    return _get_attr(node, ATTR_VERIFIER)


def read_fingerprint(node):
    """
    """
    return _get_attr(node, ATTR_FINGERPRINT)


def read_uuid(node):
    """
    """
    muuid = cmds.ls(node, uuid=True)
    if not len(muuid):
        raise RuntimeError("Node not found.")
    elif len(muuid) > 1:
        raise RuntimeError("Found more then one node, use long name.")

    return muuid[0]


def _generate_address():
    """
    """
    try:
        return str(bson.ObjectId())  # bson is faster
    except NameError:
        return str(uuid.uuid1())[:-18]  # remove mac-addr


def _generate_verifier(muuid, address):
    """Generate a hash value from Maya UUID and address

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
    """
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
    """
    """
    origin_fingerprint = read_fingerprint(node)

    if origin_fingerprint is None:
        # Node did not have the attributes for verification,
        # this is new node.
        return True
    else:
        return not fingerprint == origin_fingerprint


def _update_verifier(node, address):
    """
    """
    _add_attr(node, ATTR_VERIFIER)
    verifier = _generate_verifier(read_uuid(node), address)
    _set_attr(node, ATTR_VERIFIER, verifier)


def _update_fingerprint(node, fingerprint):
    """
    """
    _add_attr(node, ATTR_FINGERPRINT)
    _set_attr(node, ATTR_FINGERPRINT, fingerprint)


def is_update_required(node, fingerprint):
    """
    """
    if is_changed(node, fingerprint) and is_duplicated(node):
        return True
    return False


def update_identity(node, fingerprint):
    """
    """
    _add_attr(node, ATTR_ADDRESS)
    address = _generate_address()
    _set_attr(node, ATTR_ADDRESS, address)
    _update_fingerprint(node, fingerprint)


def lock_identity(nodes):
    """
    """
    for node in nodes:
        address = read_address(node)
        if address is not None:
            _update_verifier(node, address)


def get_time(node):
    """Retrive datetime object from Maya node

    A little bonus gained from datetime embedded id

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
