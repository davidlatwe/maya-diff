<h1 align=center>Maya-Diff</h1>

<p align=center><i><b>An ID renew logic for modification tracking in Maya pipeline</b>,<br>that able to tell you which node is untracked and need identity update in production.<br>(require node hashing for change detection)</br></i></p>


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


### Example Usage

##### On publish or save
```python
import mdiff.api

for node in nodes:
    # make fingerprint
    fingerprint = my_hasher(node)

    if mdiff.api.is_update_required(node, fingerprint):
        # do something
        ...

        mdiff.api.update_identity(node, fingerprint)

    else:
        # do some other thing
        ...

mdiff.api.lock_identity(nodes)

```

##### On import
```python
import mdiff.api

nodes = cmds.file("path/to/scene", i=True, returnNewNodes=True)
mdiff.api.lock_identity(nodes)

```
