<h1 align=center>Maya-Diff</h1>

<p align=center><i><b>An ID renew logic for modification tracking in Maya pipeline</b>,<br>that able to tell you which node is untracked and need identity update on demand.<br>(require node hashing for change detection)</br></i></p>


<p align=center><i>This is a proof of concept, currently testing in production</i></p>


### Motivation

When using custom ID on nodes for mapping with other nodes or data that need to connect with or apply to, might require to ensure the node IDs in one artist's scene are consisted with or tracked in pipeline. That wasn't easy, especially after file-import or node's duplication happened.

Therefore, I want to find a way to answer the following questions:

1. These nodes shared same ID, but which node is original ? or duplicated ?
2. Has this node been modified ?
3. Does this node have to renew it's ID ?


### Implementation

First, I need to rephrase `Custom ID` to `address`, since it's an ID for lookup in the scene when mapping changes back to nodes.

And here's what we will have in each tracked node:

* UUID

    In each node we have a Maya UUID by default, UUID will stay the same when the node is a referenced node, but not imported or duplicated.

* Address

    A pipeline custom ID for node, we will use a timestamp embedded ID, `uuid1` or `bson.ObjectId`.

* Verifier

    This is a hash value generated from hashing `UUID` and `Address`, for us to recognize duplicated node, no matter the node is imported or referenced.

* Fingerprint

    This is a hash value that need to be generated from **custom node hasher** *(not included in `mdiff`)*. For mesh type nodes, you may generate from hashing every vertices position, normals and UVs. For shader, you may generate from hashing every attribute value with the shader type name, even with texture file. *The point is, you need to produce a string value that able to help `mdiff` to identify changes that you want to be awared of*.

Now, we can answer those three questions:

1. **These nodes shared same ID, but which node is original ? or duplicated ?**

    By hashing `uuid` and `address` again, and compare the value with `verifier`, if it's not equal, then this is a duplicated node. This will work is because the Maya UUID will change when the node get duplicated, thus the hash value of `uuid` and `address` will change, too. (To work on imported nodes, we need to generate `verifier` right after the nodes get imported.)

2. **Has this node been modified ?**

    If you have your custom node hasher ready, then this one is easy. Just hash the node again and compare the value with `fingerprint` attribute.

3. **Does this node have to renew it's ID ?**

    * No, if
        * Node is original and not changed
        * Node is duplicated and not changed
        * Node has been changed but is original
    * Yes, if
        * Node is newly created
        * Node is duplicated and has been changed


### Demo

A simple walkthrough

##### Preparation

```python
import maya.cmds as cmds
import mdiff.api

# Make a simple transfrom matrix hasher
matrix_hasher = (lambda node: str(cmds.xform(node, query=True, matrix=True)))

```

##### Create a new asset

```python
node = cmds.polyCube(name="origin")[0]
# Hash it
fingerprint = matrix_hasher(node)
# Since this is a new node, renew is a must
state = mdiff.api.status(node, fingerprint)
assert state == mdiff.api.Untracked
# Register
mdiff.api.on_track(node, fingerprint)

```

##### Change

```python
# Move the node around
cmds.setAttr(node + ".tx", 5)
# Hash it
fingerprint = matrix_hasher(node)
# Check
state = mdiff.api.status(node, fingerprint)
assert state == mdiff.api.Changed
# it's been changed but is original, update fingerprint
mdiff.api.on_change(node, fingerprint)

```

##### Duplicate

```python
clone = cmds.duplicate(node, name="clone")[0]
# Check
fingerprint = matrix_hasher(clone)
state = mdiff.api.status(clone, fingerprint)
assert state == mdiff.api.Duplicated
# Although it's not changed but is a duplicate, update verifier
mdiff.api.on_duplicate(clone)

```

##### Duplicate & Change

```python
rogue = cmds.duplicate(node, name="rogue")[0]
# Now move the rogue !
cmds.setAttr(rogue + ".ty", 10)
# Check
fingerprint = matrix_hasher(rogue)
state = mdiff.api.status(rogue, fingerprint)
assert state == mdiff.api.Untracked
# it's been changed and is a duplicate, need to renew !
mdiff.api.on_track(rogue, fingerprint)

```

To simplify, you can use `api.manage`

```python
foo = "A node that you don't need to overwatch"
fingerprint = my_hasher(foo)
state = mdiff.api.status(foo, fingerprint)
# Auto update node by state
mdiff.api.manage(foo, fingerprint, state)

```


### Example Usage

##### On publish or save
```python
import mdiff.api

for node in nodes:
    # Make fingerprint
    fingerprint = my_hasher(node)
    # Check status
    state = mdiff.api.status(node, fingerprint)
    # Auto management
    mdiff.api.manage(node, fingerprint, state)

```

OR

```python
import mdiff.api

for node in nodes:
    # make fingerprint
    fingerprint = my_hasher(node)
    # Check status
    state = mdiff.api.status(node, fingerprint)
    # Manual management
    if state == mdiff.api.Untracked:
        ...  # do something
        mdiff.api.on_track(node, fingerprint)

    elif state == mdiff.api.Changed:
        ...  # do something
        mdiff.api.on_change(node, fingerprint)

    elif state == mdiff.api.Duplicated:
        ...  # do something
        mdiff.api.on_duplicate(node)

```

##### On import
```python
import mdiff.api

nodes = cmds.file("path/to/scene", i=True, returnNewNodes=True)
# Update identity on Maya UUID changed
mdiff.api.update_verifiers(nodes)

```
