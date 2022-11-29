try:
    from base import Base
    from cursor_FSS import file_open, file_save
except ImportError as error:
    print(error)

class MET_Worker(Base):
    """
    Sub-class of Base for the MET base setup
    
    Methods
    -------
    - build_MET() -> MET_Worker : constructs four variations to the MET that can be used to look up values
    - start() -> dict, dict : the start method of the MET_Worker module
    """
    def __init__(self, rows:list, cols:list, data:list=None):
        super().__init__('met')

        self.rows = rows
        self.cols = cols
        self.data = data

        self.MET_Simple = {}
        self.MET_SimpleReversed = {}
        self.MET_Logical = {}
        self.MET_Dictionary = {}

    def build_MET(self):
        """
        Constructs four variations to the MET that can be used to look up values

        Parameters
        ----------

        Returns
        -------
        - self (MET_Worker) : the instance of the class used by Module to call the worker method on this instance Base class
        """

        def generate_met_simple():
            """
            Generates and stores a simple MET dictionary for fast lookup
            """
            if not file_open('compiled', 'met_simple', self.module_type, False):
                self.MET_Simple = { "_".join(x['CN']) : x['Term'].lower() for x in met_compiled }
                file_save('compiled', 'met_simple', self.MET_Simple, self.module_type)
            else:
                self.MET_Simple = file_open('compiled', 'met_simple', self.module_type)

        def generate_met_reversed():
            """
            Generates and stores a simple MET dictionary for fast reverse lookup with keys-values switched
            """
            if not file_open('compiled', 'met_simple_reversed', self.module_type, False):
                if not len(self.MET_Simple): generate_met_simple()
                for k, v in self.MET_Simple.items():
                    if v not in self.MET_SimpleReversed:
                        self.MET_SimpleReversed[v] = k
                    else:
                        codes = [self.MET_SimpleReversed[v]] if type(self.MET_SimpleReversed[v]) is str else [x for x in self.MET_SimpleReversed[v]]
                        codes.append(k)
                        self.MET_SimpleReversed[v] = codes
                self.MET_SimpleReversed = dict(sorted(self.MET_SimpleReversed.items(), key=lambda x: x[0].lower()))
                file_save('compiled', 'met_simple_reversed', self.MET_SimpleReversed, self.module_type)
            else:
                self.MET_SimpleReversed = file_open('compiled', 'met_simple_reversed', self.module_type)
        
        def generate_met_logical():
            """
            Generates and stores a logical tree of the MET code path values

            Methods
            -------
            - addLevel(path=list, MET_logical=dict, i=int) -> dict : recursive function to add new levels to the MET logical tree
            """

            def addLevel(path:str, MET_logical:dict, i:int):
                """
                A recusive private function that adds a new level to the MET_logical tree
                
                Parameters
                ----------
                - path (list) : list with logical path elements
                - MET_logical (dict) : dictionary with logical values
                - i (int) : counter in the recursive loop

                Returns
                -------
                - MET_logical (dict) : dictionary with logical values
                """
                if len(path) == 1: 
                    MET_logical[path[0]] = {}
                else:
                    i = i+1
                    keys = list(MET_logical.keys())
                    
                    if keys[keys.index(path[0])] not in MET_logical:
                        MET_logical[keys[keys.index(path[0])]] = { path[1] : {} }

                    addLevel(path[1:], MET_logical[path[0]], i)
                return MET_logical

            if not file_open('compiled', 'met_logical', self.module_type, False):
                for term in met_compiled:
                    self.MET_Logical = addLevel(term['CN'], self.MET_Logical, 1)
                file_save('compiled', 'met_logical', self.MET_Logical, self.module_type)
            else:
                self.MET_Logical = file_open('compiled', 'met_logical', self.module_type)

        def generate_met_dictionary():
            """
            Generates and stores a tree of the MET term values

            Methods
            -------
            - addTerm(path=list, term=str, MET_dictionary=dict, MET_Logical=dict) -> dict : recursive function to add new levels to the MET logical tree
            """

            def addTerm(path:list, term:str, MET_dictionary:dict, MET_logical:dict):
                """
                A recusive private function that adds a new level to the MET_dictionary tree
                
                Parameters
                ----------
                - path (list) : a list with logical path elements
                - term (str) : term to add
                - MET_dictionary (dict) : the MET_dictionary to add to
                - MET_logical (dict) : the MET_logical with logical paths

                Returns
                -------
                - MET_dictionary (dict) : the MET dictionary
                """
                if len(path) == 1:
                    MET_dictionary[term] = {}
                else:
                    keys = list(MET_logical.keys())
                    key = keys.index(path[0])
                    if len(list(MET_dictionary.keys())) < key:
                        cat = list(MET_dictionary.keys())[key]
                    else:
                        key = key - len(list(MET_dictionary.keys()))
                        cat = list(MET_dictionary.keys())[key]
                    if cat not in MET_dictionary:
                        MET_dictionary[cat] = { term : {} }
                    addTerm(path[1:], term, MET_dictionary[cat], MET_logical[path[0]])

                return MET_dictionary

            if not file_open('compiled', 'met_dictionary', self.module_type, False):
                if not len(self.MET_Logical): generate_met_logical()
                for term in met_compiled:
                    self.MET_Dictionary = addTerm(term['CN'], term['Term'], self.MET_Dictionary, self.MET_Logical)
                file_save('compiled', 'met_dictionary', self.MET_Dictionary, self.module_type)
            else:
                self.MET_Dictionary = file_open('compiled', 'met_dictionary', self.module_type)
                
        
        # THE FILE 'met' CONTAINS ALL REVELANT DATA TO GENERATE THE MET DATA REQUIRED TO UPDATE ALL RECORDS
        # THIS FILE ORIGINATES FROM THE TERMS AND TERMMASTER TABLES IN THE GICARDTMSTHESTEST DATABASE
        try:
            met_compiled = file_open('compiled', 'met_compiled', self.module_type)

            # COMBINE ROWS AND COLS TO SINGLE DICTIONARY
            met_compiled = [{ y : row[self.cols.index(y)] for y in self.cols } for row in self.rows]
            met_compiled = [{ k : int(v) if 'NodeDepth' in k else v for k, v in x.items() } for x in met_compiled]
            met_compiled = [{ k : v.split('.') if 'CN' in k else v for k, v in x.items() } for x in met_compiled]

            # THE ORDER OF CN ELEMENTS IS IMPORTANT TO PROPERLY GENERATE THE MET DICTIONARY FILES
            met_compiled = sorted(met_compiled, key=lambda v: v['CN'])
                
            # STORE THE FILE FOR LATER REUSE
            file_save('compiled', 'met_compiled', met_compiled, self.module_type)
        
            # AT THIS POINT WE CAN GENERATE FOUR DIFFERENT VERSIONS OF THE MET
            generate_met_simple()
            generate_met_reversed()
            generate_met_logical()
            generate_met_dictionary()
        except:
            raise

        return self

    def start(self):
        """
        The start method of the MET_Worker module.
        1) Iterates over all values from the ThesXRefs query
        2) Updates all values with paths based on the MET files generated in build_MET()

        Returns
        -------
        - self.relations (dict) : data relevant to manifest generation derived from the media records (these are media from the ThesXRefs table)
        - dict : processing results
        """

        rows = [{ y : row[self.data[0]['cols'].index(y)] for y in self.data[0]['cols'] } for row in self.data[0]['rows']]

        def findPath(code:str):
            """
            This method returns a path for a value-lookup in MET.
            
            Parameters
            ----------
            - code (str) : CN code to analyze

            Returns
            -------
            - codes (list) : a list of codes
            - list : a list of terms that belong with the paths
            ##### OR
            - code (str) : the original single code
            - list : the corresponding MET term
            """
            if '.' in code:
                code = code.split('.')
                codes = ["_".join(code[:idx+1]) if len(code) > 1 else code[:idx+1] for idx, c in enumerate(code)]
                return codes, [self.MET_Simple[code] for code in codes]
            else:
                return code, self.MET_Simple[code]

        # RESOLVE ALL CODES TO COMPLETE PATHS
        for row in rows:
            try:
                row = self.sanitize(row)

                if row['MediaMasterID'] not in self.relations: self.relations[row['MediaMasterID']] = []

                row['Codes'] = findPath(row['CN'])[0]
                row['Paths'] = findPath(row['CN'])[1]

                self.relations[row['MediaMasterID']].append(row)
            except:
                # NOTE: MediaMasterID 1521 has a problematic code (AAE.AAC.AAE.AAO), which apparently relates
                # to another definition of MET in TMS. This will therefore throw an error, but this is a minor problem.
                continue

        return self.records, self.relations, self.thumbnail_urls, { 'MET_worker_res' : 0, 'MET_worker_err' : 0 }