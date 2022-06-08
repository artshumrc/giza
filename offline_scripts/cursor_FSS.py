try:
    from json import JSONEncoder, loads, dumps
    from os.path import exists
    from os import remove, mkdir
    from shutil import rmtree
    from sql import SQL
except ImportError as error:
    print(error)

class SetEncoder(JSONEncoder):
    def default(self, obj):
        return list(obj)

def file_open(folder:str, file:str, module:str, open_file:bool=True):
    """
    This method checks if a .json-file exists at a given path, can be successfully read, 
    and optionally returns the contents of that file.

    Parameters
    ----------
    folder : str
        Subfolder in offline_scripts
    file : str
        Filename
    module : str
        Module name calling the method
    open_file : bool
        Boolean whether the file should be read in memory entirely

    Returns
    -------
    - dict : json file contents, or
    - bool : True/False locating/reading file
    """
    file = file if 'json' in file else f'{file}.json'
    dir = f'offline_scripts/{module}/{folder}'
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

def file_save(folder:str, file:str, data:list, module:str):
    """
    This method saves a .json-file exists at a given path, can be successfully read, 
    and optionally returns the contents of that file.

    Parameters
    ----------
    folder : str
        Subfolder in offline_scripts
    file : str
        Filename
    data : list
        List of dictionaries containing data
    module : str
        Module name calling the method

    Returns
    -------
    None
    """
    file = file if 'json' in file else f'{file}.json'
    base_dir = f'offline_scripts/{module}'
    dir = f'{base_dir}/{folder}'
    
    if not exists(dir):
        if not exists(base_dir): mkdir(base_dir)
        mkdir(dir)

    with open(f'{dir}/{file}', 'w') as f:
        f.write(dumps(data, indent=4, separators=(',',':'), sort_keys=True, cls=SetEncoder))

def file_del(module:str, folder:str, filename:str=''):
    """
    This method checks if a .json-file exists at a given path and 
    deletes that file if it does indeed exist. Otherwise returns False.
    If no filename is passed in, the method will remove the folder instead.

    Parameters
    ----------
    - module (str) : module name calling the method
    - folder (str) : subfolder in offline_scripts
    - filename (str) : filename (optional)

    Returns
    -------
    - bool (optional): True/False locating/deleting file
    """
    dir = f'offline_scripts/{module}/{folder}'
    
    if filename:
        filename = filename if '.json' in filename else f'{filename}.json'
        
    if exists(f'{dir}/{filename}'):
        try:
            remove(f'{dir}/{filename}') if filename else rmtree(f'{dir}')
        except:
            return False
    else:
        return False

def tables_exists(folder:str, file:str, module:str, modules:list=None):
    """
    This method checks if a .json-file exists at a given path and 
    deletes that file if it does indeed exist. Otherwise returns False

    Parameters
    ----------
    folder : str
        Subfolder in offline_scripts
    file : str
        Filename
    module : str
        Module name calling the method
    modules : list
        List of module names to check tables for

    Returns
    -------
    - dict : json file contents, or
    - bool (optional): True/False locating files when a list of modules is passed in
    """
    # CHECK A SPECIFIC TABLE IN A FOLDER
    if folder and file:
        return file_open(folder, file, module, False)
    
    # CHECK ALL TABLES OF A LIST OF MODULES
    else:
        complete_modules = []
        
        if not modules: modules = list([key for key in SQL.keys()])
        
        tables = { module : [table for table in SQL[module]] for module in modules }
        
        for module in modules:
            existing_tables = []
            for table in tables[module]:
                existing_tables.append(file_open('tables', f'{table}.json' if module in table else f'{module}_{table}.json', module, False))
            
            if len(existing_tables) == len(tables[module]): complete_modules.append(True)

        return True if len(complete_modules) == len(tables) else False