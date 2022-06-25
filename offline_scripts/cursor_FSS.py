try:
    from os import remove, mkdir, listdir
    from os.path import exists
    from shutil import rmtree
    from json import JSONEncoder, loads, dumps
    from sql import SQL
except ImportError as error:
    print(error)

class SetEncoder(JSONEncoder):
    def default(self, obj):
        return list(obj)

def file_open(dir:str, file:str, module:str=None, open_file:bool=True):
    """
    This method checks if a .json-file exists at a given path, can be successfully read, 
    and optionally returns the contents of that file.

    Parameters
    ----------
    - dir (str) : folder
    - file (str) : filename
    - module (str) : module name calling the method (optional)
    - open_file (bool) : boolean whether the file should be read in memory entirely

    Returns
    -------
    - dict : json file contents, or
    - bool : True/False locating/reading file
    """
    if dir and module:
        dir = f'offline_scripts/{module}/{dir}'

    if file:
        file = file if 'json' in file else f'{file}.json'
    
    if exists(f'{dir}/{file}'):
        try:
            with open(f'{dir}/{file}') as f:
                if not open_file:
                    f.seek(0)
                    data = f.read(0-100)
                    if type(data) is str and data.startswith('{\n'):
                        return True
                else:        
                    file = f.read()
                    if len(file):
                        return loads(file)
                    else:
                        return False
        except:
            return False
    else:
        return False

def file_save(dir:str, file:str, data:list, module:str=None):
    """
    This method saves a .json-file exists at a given path, can be successfully read, 
    and optionally returns the contents of that file.

    Parameters
    ----------
    - folder (str) : folder
    - file (str) : filename
    - data (list) : list containing data
    - module (str) : module calling the method (optional)
    """

    if dir and module:
        base_dir = f'offline_scripts/{module}'
        dir = f'{base_dir}/{dir}'

    if file:
        file = file if 'json' in file else f'{file}.json'
    
    if not exists(dir):
        if not exists(base_dir): mkdir(base_dir)
        mkdir(dir)

    with open(f'{dir}/{file}', 'w') as f:
        f.write(dumps(data, indent=4, separators=(',',':'), sort_keys=True, cls=SetEncoder))

def file_del(module:str, folder:str, filename:str='', exclude:list=[]) -> bool:
    """
    This method checks if a .json-file exists at a given path and 
    deletes that file if it does indeed exist. Otherwise returns False.
    If no filename is passed in, the method will remove the folder instead.

    Parameters
    ----------
    - module (str) : module name calling the method
    - folder (str) : subfolder in offline_scripts
    - filename (str) : filename (optional)
    - exclude (list) : list of filename strings to exclude from deletion process

    Returns
    -------
    - bool (optional): True/False locating/deleting file
    """
    dir = f'offline_scripts/{module}/{folder}'
    
    if filename:
        filename = filename if '.json' in filename else f'{filename}.json'

    if exists(f'{dir}/{filename}'):
        try:
            if not len(exclude):
                remove(f'{dir}/{filename}') if filename else rmtree(f'{dir}')
            else:
                files = listdir(dir)
                for filename in exclude:
                    filename = filename if '.json' in filename else f'{filename}.json'
                    if filename in files: files.remove(filename)
                for filename in files:
                    remove(f'{dir}/{filename}')
        except:
            return False
    else:
        return False

def list_folder(folder:str):
    try:
        return listdir(folder)
    except Exception as e:
        raise e

def get_thumbnails(module=None):
    """
    Checks how many thumbnails currently exist in the static folder. The program keeps track of
    the number of thumbnails in thumbnails.json, which lives in the static/images/thumbnails folder.
    As each module processes its thumbnails, that file is updated to reflect the process for each module.
    The file should be empty at the end of the entire program's run at which point this method will
    re-read the folder and rebuild a fresh thumbnails.json-file.
    
    Returns
    -------
    - thumbnails (list) : a list of all file-names in the static/images/thumbnails folder
    """

    # SAVE THUMBNAILS TO THE STATIC FOLDER
    base_dir = f'static/images'
    dir = f'{base_dir}/thumbnails'

    if not exists(dir):
        if not exists(base_dir): mkdir(base_dir)
        mkdir(dir)

    try:
        thumbnails = file_open(dir, 'thumbnails', open_file=True)
        
        if module:
            thumbnails = thumbnails[module]
        
        if not thumbnails or not len(thumbnails) or not module:
            return [file.split('.')[0] for file in list_folder(dir)]
        
        return thumbnails
    except:
        
        # RETURN ALL IF WE CAN'T OPEN THE FILE OR RETURN ONLY THOSE APPLICABLE TO THE MODULE
        return [file.split('.')[0] for file in list_folder(dir)]

def save_thumbnails(module, thumbnails):
    
    # SAVE THUMBNAILS TO THE STATIC FOLDER
    base_dir = f'static/images'
    dir = f'{base_dir}/thumbnails'

    if not exists(dir):
        if not exists(base_dir): mkdir(base_dir)
        mkdir(dir)

    try:
        thumbnails_from_file = file_open(dir, 'thumbnails', open_file=True)
        if not thumbnails_from_file:
            thumbnails_from_file = {}
        thumbnails_from_file[module] = thumbnails
        file_save(dir, 'thumbnails', thumbnails_from_file)
        return thumbnails_from_file[module]
    except:
        return False

def tables_exists(folder:str=None, file:str=None, module:str=None, modules:list=None):
    """
    Checks if a tables of a particular module exist at a given path.
    The path is formed by folder and file, and typically a module as this method
    is often called within active modules. If an (empty) list of modules is passed in
    the method will check either all tables in the list, or all tables for all modules,
    in case the list is empty.

    Parameters
    ----------
    - folder (str) : subfolder in offline_scripts, typically the same as module name (optional)
    - file (str) : filename in offline_scripts (optional)
    - module (str) : name of module calling the method (optional)
    - modules (list) : list with names of module folders to check (optional)

    Returns
    -------
    - dict : json file contents
    ##### OR
    - bool : if list of modules is passed in
    """
    # CHECK A SPECIFIC TABLE IN A FOLDER
    if folder and file and not modules:
        return file_open(folder, file, module, False)
    
    # CHECK ALL TABLES OF A LIST OF MODULES
    else:
           
        complete_modules = []
        
        if not modules: modules = list([key for key in SQL.keys()])

        if module is not None:
            modules = [module]
        
        tables = { module : [table for table in SQL[module]] for module in modules }
        
        for module in modules:
            existing_tables = []
            for table in tables[module]:
                existing_tables.append(file_open('tables', f'{table}.json' if module in table else f'{module}_{table}.json', module, False))
            
            if len(existing_tables) == len(tables[module]): complete_modules.append(True)

        return True if len(complete_modules) == len(tables) else False