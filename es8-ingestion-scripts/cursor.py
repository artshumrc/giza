try:
    from cursor_TMS import TMS
    from cursor_ES import ES
    from cursor_FSS import tables_exists
    from sql import SQL
except ImportError as error:
    print(error)

class Cursor:
    """ 
    Cursor is a general purposes facilitator for connectivity to TMS and ES.

    Methods
    -------
    - check_connections -> bool : checks connections to TMS and ES
    - local_tables -> bool|any : confirms what the user wants to do next
    """
    def __init__(self, args):
        self.tms = TMS()
        self.es = ES()
        self.args = args

    def check_es_connection(self):
        """
        Determine if connection can be established to Elasticsearch
        Raises
        ------
        - ConnectionError : could not establish connection to ElasticSearch
        """
        try:
            if not self.es.check_connection() and len([arg for arg in [arg for arg in self.args if arg.startswith('es')] if self.args[arg]]): return False
        except:
            raise ConnectionError("Could not establish connection to ElasticSearch.")
    

    def check_tms_connection(self):
        """
        Determine if connection can be established to TMS
        Raises
        ------
        - ConnectionError : could not establish connection to TMS or local files
        """
        try:
            if not self.tms.check_driver():
            
                # LOCAL TABLES:
                if self.local_tables():
                    # HALT EVERYTHING IF TABLES NOT THERE OR CORRUPT
                    return True if tables_exists(modules=self.args.modules) else False
                else:
                    # FULL STOP: WE EITHER NEED A CONNECTION TO TMS OR ACCESS TO LOCAL TABLES
                    raise ConnectionError("Could not establish connection to TMS or local files.")
            else:
                return True
        except:
            raise ConnectionError("Could not establish connection to TMS or local files.")


    # def check_connections(self):
    #     """
    #     This method determines if connections can be established to ElasticSearch and either TMS or local files

    #     Raises
    #     ------
    #     - ConnectionError : could not establish connection to TMS and/or ElasticSearch
    #     """
    #     try:
            

    #         # CONNECTION TO ES: HALTS EVERYTHING IF REQUIRED AND FAILS
    #         if not self.es.check_connection() and len([arg for arg in [arg for arg in self.args if arg.startswith('es')] if self.args[arg]]): return False

    #         # CONNECTION TO TMS: HALTS EVERYTHING IF REQUIRED AND FAILS
    #         if not self.tms.check_driver():
            
    #             # LOCAL TABLES:
    #             if self.local_tables():

    #                 # HALT EVERYTHING IF TABLES NOT THERE OR CORRUPT
    #                 return True if tables_exists(modules=self.args.modules) else False

    #             else:

    #                 # FULL STOP: WE EITHER NEED A CONNECTION TO TMS OR ACCESS TO LOCAL TABLES
    #                 raise
            
    #         else:
    #             return True
    #     except:
    #         raise ConnectionError("Could not establish connections to TMS and/or ElasticSearch.")

    def local_tables(self):
        """ 
        Prompt the user in case connection to TMS fails.
        """
        try:
            def parse_response(response):
                """
                Parse the response of the user.
                
                Parameters
                ----------
                - response (str) : whatever the user puts in

                Returns
                -------
                - Boolean : either True or False
                #### OR
                - Function : function call to check_connections or local_tables
                """
                response = response.lower()
                responses_negative = ['n']
                responses_positive = ['y', 'r']
                if response in responses_negative:
                    return False
                elif response in responses_positive:
                    if response == 'r':
                        return self.check_connections()
                    else:
                        return True
                else:
                    return self.local_tables()
        
            # return parse_response(input("Try with local tables instead (y/n) or retry (r)?"))
            return True
        except:
            raise FileNotFoundError("Could not find necessary files")