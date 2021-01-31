import filecmp
import os
import random
import shutil
import sys
from time import gmtime, strftime

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from graphviz import Digraph

# the current directory is not always the folder you want to backup
## make sure to make cd the relevant folder you want to backup


def init():
    cwd = os.getcwd()
    new_path = cwd + r"\.wit"
    images_path = new_path + "\images"
    staging_area_path = new_path + "\staging_area"
    try:
        os.mkdir(new_path)
    except FileExistsError:
        print("This location already has a backup .wit folder.")
    else:
        os.mkdir(images_path)
        os.mkdir(staging_area_path)
        print(f"Backup .wit folder created at: {new_path}")
        activate("master")


def seek_wit(path):
    if os.path.isfile(path):
        start = os.path.abspath(path + "\..")
    else:
        start =  os.path.abspath(path)
    max_iterations = len(start.split("\\"))
    folders_to_create = []
    for i in range(max_iterations):
        parent = start
        if ".wit" in os.listdir(parent):
            return True, folders_to_create, parent
        folders_to_create.insert(0, parent.split("\\")[-1])
        start = os.path.abspath(parent + "\..")
    return False

class NoWitError(Exception):
    pass

def copy_and_overwrite_folder_contents(old_path, new_path):
    folder_contents = os.listdir(old_path)
    for i in folder_contents:
        current_location = os.path.join(old_path, i)
        new_location = os.path.join(new_path, i)
        if i in os.listdir(new_path):
            os.remove(new_location)
        if os.path.isfile(current_location):
            shutil.copy(current_location, new_location)
        else:
            shutil.copytree(current_location, new_location)

def add(path):
    full_path = os.path.abspath(path)
    seek = seek_wit(path)
    if not seek[0]:
        raise NoWitError(f".wit backup doesnt exist in hirarchy of backup folder/file")
    folders_to_create = seek[1]
    wit_location = seek[2]
    start = os.path.join(wit_location, ".wit\staging_area")
    for i in folders_to_create:
        new_path = os.path.join(start, i)
        try:
            os.mkdir(new_path)
        except FileExistsError:
            print(f"location \"{new_path}\" already exists")
        start = new_path
    if os.path.isfile(path):
        file_name = os.path.basename(path)
        shutil.copyfile(path, os.path.join(start, file_name))
    else:
        copy_and_overwrite_folder_contents(path, start)
    print(f"Add of {path} completed successfully")

def name_gen():
    options = "1234567890abcdef"
    new_str = ""
    for i in range(40):
        new_str += random.choice(options)
    return new_str

def commit(message, second_parent = False):
    full_path = os.path.abspath(os.getcwd())
    seek = seek_wit(full_path)
    if not seek[0]:
        raise NoWitError(f".wit backup doesnt exist in hirarchy of backup folder/file")
    print("commit started")
    commit_id = name_gen()
    wit_location = seek_wit(os.getcwd())[2]
    ref_path = os.path.join(wit_location, ".wit\\references.txt")
    if not os.path.isfile(ref_path):
        with open(ref_path, "w") as ref:
            ref.write("HEAD=None\nmaster=None")
    images_path = os.path.join(wit_location, ".wit\images")
    new_file_path = os.path.join(images_path, commit_id)
    os.mkdir(new_file_path)
    current_datetime = strftime("%a %d %b %Y %H:%M:%S %z", gmtime())
    parent = get_last_commit()
    if second_parent != False:
        parent = parent + ", " + second_parent
    txt = f"parent={parent}\ndate={current_datetime}\nmessage={message}"
    metadata_path = new_file_path + ".txt"
    new_file = open(metadata_path, "w")
    new_file.write(txt)
    new_file.close()
    staging_area_path = os.path.join(wit_location, ".wit\staging_area")
    copy_and_overwrite_folder_contents(staging_area_path, new_file_path)
    active_branch = get_active_branch()
    if active_branch[1] == get_last_commit():
        update_branch_commit(active_branch[0], commit_id)
    update_branch_commit("HEAD", commit_id)
    print(f"commit ended: {commit_id}")

def get_last_commit():
    return get_branch_data("HEAD")[1]
    
def get_master():
    return get_branch_data("master")[1]

def update_head(new_head):
    wit_location = seek_wit(os.getcwd())[2]
    ref_path = os.path.join(wit_location, ".wit\\references.txt")
    with open(ref_path, "r") as ref:
        contents = ref.read()
    old_head = get_last_commit()
    old_string = "HEAD=" + get_last_commit()
    new_string = "HEAD=" + new_head
    new_contents = contents.replace(old_string, new_string)
    file = open(ref_path, "w")
    file.write(new_contents)
    file.close()
    print(f"HEAD updated\nfrom: {old_head} \nto: {new_head}")

def update_branch_commit(branch_name, commit_id):
    wit_location = seek_wit(os.getcwd())[2]
    ref_path = os.path.join(wit_location, ".wit\\references.txt")
    with open(ref_path, "r") as ref:
        contents = ref.read()
    old_commit = get_branch_data(branch = branch_name)[1]
    old_string = branch_name + "=" + old_commit
    new_string = branch_name + "=" + commit_id
    new_contents = contents.replace(old_string, new_string)
    file = open(ref_path, "w")
    file.write(new_contents)
    file.close()
    print(f"branch updated\nfrom: {old_commit} \nto: {commit_id}")

def print_changes_to_be_commited(dircmp_object):
    for name in dircmp_object.right_only:
        yield name
    for subdirectory in dircmp_object.subdirs.values():
        for x in print_changes_to_be_commited(subdirectory):
            yield x

def print_changes_not_staged_for_commit(dircmp_object):
    for name in dircmp_object.diff_files:
        yield name
    for subdirectory in dircmp_object.subdirs.values():
        for x in print_changes_not_staged_for_commit(subdirectory):
            yield x

def get_common_file_names(dircmp_object):
    for name in dircmp_object.common:
        yield name
    for subdirectory in dircmp_object.subdirs.values():
        folder = subdirectory.right.split("\\")[-1]
        for x in get_common_file_names(subdirectory):
            yield os.path.join(folder, x)

def get_left_file_names(dircmp_object):
    for name in dircmp_object.left_only:
        yield name
    for subdirectory in dircmp_object.subdirs.values():
        folder = subdirectory.right.split("\\")[-1]
        for x in get_left_file_names(subdirectory):
            yield os.path.join(folder, x)

def status(to_print = True):
    full_path = os.path.abspath(os.getcwd())
    seek = seek_wit(full_path)
    if not seek[0]:
        raise NoWitError(f".wit backup doesnt exist in hirarchy of backup folder/file")
    last_commit = get_last_commit()
    wit_location = seek[2]
    last_commit_path = os.path.join(wit_location, ".wit\images\\" + last_commit)
    staging_area_path = os.path.join(wit_location, ".wit\staging_area")
    obj_last_commit_staging = filecmp.dircmp(last_commit_path, staging_area_path, ignore = [".wit"])
    obj_staging_orig = filecmp.dircmp(staging_area_path, full_path, ignore = [".wit"])
    ctbc = [x for x in print_changes_to_be_commited(obj_last_commit_staging)]
    cnsfc = [x for x in print_changes_not_staged_for_commit(obj_staging_orig)]
    uf = [x for x in print_changes_to_be_commited(obj_staging_orig)]
    if to_print == True:
        print(f"folder that is being backed up:\n{full_path}")
        print("-" * 15)
        print(f"commit id: {last_commit}")
        print("-" * 15)
        print("changes to be commited:")
        print("-" * 15)
        print(ctbc)
        print("-" * 15)
        print("changes not staged for commit:")
        print("-" * 15)
        print(cnsfc)
        print("-" * 15)
        print("untracked files:")
        print("-" * 15)
        print(uf)
        print("-" * 15)
    return ctbc, cnsfc, uf

def iter_through_files():
    for obj in os.listdir():
        print(os.path.abspath(obj))

def checkout(commit_id):
    if commit_id in get_branch_name_list():
        branch_data = get_branch_data(commit_id)
        commit_id = branch_data[1]
        activate(branch_data[0])
        print(f"checking out with branch: {branch_data[0]}")
    else:
        activate("")
    full_path = os.path.abspath(os.getcwd())
    seek = seek_wit(full_path)
    wit_location = seek[2]
    if not seek[0]:
        raise NoWitError(f".wit backup doesnt exist in hirarchy of backup folder/file")
    origin = os.path.join(wit_location, ".wit\images\\" + commit_id)
    status_lists = status(to_print = False)
    if len(status_lists[0]) > 0:
        print(f"there are still changes to be commited:\n{status_lists[0]}")
    if len(status_lists[1]) > 0:
        print(f"There are changes that were not commited yet:\n{status_lists[1]}")
    #last_commit = get_last_commit()
    images_path = os.path.join(wit_location, ".wit\images")
    if commit_id not in os.listdir(images_path):
        branch_data = get_active_branch() 
        commit_id = branch_data[1]
    commit_path = os.path.join(images_path, commit_id)
    staging_area_path = os.path.join(wit_location, ".wit\staging_area")
    obj_commit_to_orig = filecmp.dircmp(commit_path, full_path, ignore = [".wit"]) 
    filenames = [x for x in get_common_file_names(obj_commit_to_orig)]
    curr_path_dest = full_path
    curr_path_orig = commit_path
    for x in filenames:
        if os.path.isdir(curr_path_orig + "\\" + x):
            pass
        else:
            shutil.copy(curr_path_orig + "\\" + x, curr_path_dest + "\\" + x)
    staging_area_path = os.path.join(wit_location, ".wit\staging_area")
    shutil.rmtree(staging_area_path)
    shutil.copytree(commit_path, staging_area_path)
    update_head(commit_id)
    print(f"checkout completed, from:\n{commit_path}\nto:\{full_path}")

def get_parent(commit_id):
    if commit_id == "None":
        return None
    full_path = os.path.abspath(os.getcwd())
    seek = seek_wit(full_path)
    wit_location = seek[2]
    if len(commit_id) > 40:
        commit_id = commit_id.split(", ")[0]
    image_location = wit_location + "\.wit\images\\" + commit_id + ".txt"
    with open(image_location, "r") as file:
        content = file.readlines()
    return content[0].split("=")[1].strip()
    
def graph(expand = False):
    full_path = os.path.abspath(os.getcwd())
    seek = seek_wit(full_path)
    wit_location = seek[2]
    if not seek[0]:
        raise NoWitError(f".wit backup doesnt exist in hirarchy of backup folder/file")
    images_location = os.path.join(wit_location, ".wit\images")
    start = get_last_commit()
    master = get_master()
    parent = get_parent(start)
    w = Digraph()
    w.node("HEAD")
    w.node(start[:6])
    w.node("MASTER")
    w.node(master[:6])
    w.edge('HEAD', start[:6])
    w.edge("MASTER", master[:6])
    for i in get_branch_name_list()[2:]:
       branch_data = get_branch_data(i)
       w.node(branch_data[0])
       w.node(branch_data[1][:6])
       w.edge(branch_data[0], branch_data[1][:6])
    if expand == False:
        if len(parent) > 40:
            for par in parent.split(", "):
                w.edge(start[:6], par[:6])
        else:
            w.edge(start[:6], parent[:6])
        w.view()
    if expand == True:
        n = int(len(os.listdir(images_location))/2)
        for i in range(n):
            parent = get_parent(start)
            if parent == None:
                break
            if len(parent) > 40:
                for par in parent.split(", "):
                    w.edge(start[:6], par[:6])
                start = parent.split(", ")[0]
            else:
                w.edge(start[:6], parent[:6])
                start = parent
        w.view()

def branch(NAME):
    full_path = os.path.abspath(os.getcwd())
    seek = seek_wit(full_path)
    wit_location = seek[2]
    if not seek[0]:
        raise NoWitError(f".wit backup doesnt exist in hirarchy of backup folder/file")
    ref_path = os.path.join(wit_location, ".wit\\references.txt")
    HEAD = get_last_commit()
    txt = "\n" + NAME + "=" + HEAD
    with open(ref_path, "a") as ref:
        ref.write(txt)
    print(f"Branch created: {NAME}={HEAD}")

def activate(NAME):
    full_path = os.path.abspath(os.getcwd())
    seek = seek_wit(full_path)
    wit_location = seek[2]
    activated_location = wit_location + "\.wit\\activated.txt"
    with open(activated_location, "w") as file:
        file.write(NAME)
    print(f"active brach: {NAME}")

def get_active_branch():
    full_path = os.path.abspath(os.getcwd())
    seek = seek_wit(full_path)
    wit_location = seek[2]
    active_path = os.path.join(wit_location, ".wit\\activated.txt")
    with open(active_path, "r") as act:
        active_branch = act.read().strip()
    return get_branch_data(active_branch)
    
def get_branch_data(branch):
    full_path = os.path.abspath(os.getcwd())
    seek = seek_wit(full_path)
    wit_location = seek[2]
    ref_path = os.path.join(wit_location, ".wit\\references.txt")
    with open(ref_path, "r") as ref:
        lines = ref.readlines()
    reffered_commit = None
    for line in lines:
        if line.strip().split("=")[0] == branch:
            reffered_commit = line.strip().split("=")[1]
            break
    return branch, reffered_commit

def get_branch_name_list():
    full_path = os.path.abspath(os.getcwd())
    seek = seek_wit(full_path)
    wit_location = seek[2]
    ref_path = os.path.join(wit_location, ".wit\\references.txt")
    with open(ref_path, "r") as ref:
        lines = ref.readlines()
        branch_names_list = [x.strip().split("=")[0] for x in lines]
    return branch_names_list

def get_common_base(branch_name):
    second_branch = get_last_commit()
    first_branch = get_branch_data(branch_name)[1]
    if first_branch == second_branch:
        return None
    parents = []
    parents.append(second_branch)
    parent = second_branch
    print(f"first branch: {first_branch}, head: {second_branch}")
    while True:
        parent = get_parent(parent)
        if len(parent) > 40:
            for par in parent.split(", "):
                parents.append(par)
            if first_branch in parent.split(", "):
                break
        else:
            parents.append(parent)
            if first_branch == parent:
                break
    return parents

def merge(branch_name):
    full_path = os.path.abspath(os.getcwd())
    seek = seek_wit(full_path)
    wit_location = seek[2]
    if not seek[0]:
        raise NoWitError(f".wit backup doesnt exist in hirarchy of backup folder/file")
    branch = False
    images_path = os.path.join(wit_location, ".wit\images")
    staging_area_path = os.path.join(wit_location, ".wit\staging_area")
    common_base = get_common_base(branch_name)
    if common_base == None:
        print("same commit, no point in merging")
        return None
    for branch in common_base:
        commit_path = os.path.join(images_path, branch)
        obj_commit_to_orig = filecmp.dircmp(commit_path, staging_area_path, ignore = [".wit"]) 
        filenames = [x for x in get_left_file_names(obj_commit_to_orig)]
        curr_path_dest = staging_area_path
        curr_path_orig = commit_path
        for x in filenames:
            if os.path.isdir(curr_path_orig + "\\" + x):
                if os.path.exists(curr_path_dest + "\\" + x):
                    pass
                else:
                   # os.mkdir(curr_path_dest + "\\" + x)
                    shutil.copytree(curr_path_orig + "\\" + x, curr_path_dest + "\\" + x)
            else:
                shutil.copy(curr_path_orig + "\\" + x, curr_path_dest + "\\" + x)
        print(f"merge completed, from:\n{commit_path}\nto:\{staging_area_path}")
    commit("merge", second_parent = branch)
    active_branch = get_active_branch()
    update_branch_commit(active_branch[0], get_last_commit())


if len(sys.argv) > 1:
    if sys.argv[1] == "init":
        init()
    if sys.argv[1] == "add":
        add(sys.argv[2])
    if sys.argv[1] == "status":
        status()
    if sys.argv[1] == "commit":
        if len(sys.argv) == 3:
            commit(sys.argv[2])
        else:
            commit("None")
    if sys.argv[1] == "checkout":
        checkout(sys.argv[2])
    if sys.argv[1] == "graph":
        if len(sys.argv) == 3:
            if sys.argv[2] == "--all":
                graph(expand = True)
        else:
            graph()
    if sys.argv[1] == "branch":
        if len(sys.argv) == 3:
            branch(sys.argv[2])
        else:
            print("please specify a branch")
    if sys.argv[1] == "merge":
        if len(sys.argv) == 3:
            merge(sys.argv[2])
        else:
            print("please specify a branch")

    

