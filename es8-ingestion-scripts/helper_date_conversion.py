try:
    from collections import Counter
    from operator import itemgetter
    from datetime import datetime
    from dateutil.parser import parser
    from cursor_FSS import file_save
    from re import compile, search, findall
except ImportError as error:
    print(error)

class Date_Conversion:
    def __init__(self, module_type):
        self.regex = compile('[@_!#$%^&*()<>?/\|}{~:]')
        self.progress = []
        self.module_type = module_type

        self.__MONTH = {
            'january' : '01',
            'february' : '02',
            'march' : '03',
            'april' : '04',
            'may' : '05',
            'june' : '06',
            'july' : '07',
            'august' : '08',
            'september' : '09',
            'october' : '10',
            'november' : '11',
            'december' : '12'
        }

        self.__COMMONALPHATYPOS = {
            'g' : '9',
            'l' : '1',
            'o' : '0'
        }

    def save_progress(self):
        file_save('logs', 'date_conversion_success', [x for x in self.progress if len(x['dates'])], self.module_type)
        file_save('logs', 'date_conversion_failures', [x for x in self.progress if not len(x['dates'])], self.module_type)

    def __convertToMS(self, value):
        """
        This method converts a properly formatted datestring to milliseconds
        ### Parameters
        - value : str
            - Date to convert (format: mm/dd/year)
        ### Returns
        - str : properly formatted datestring
        - float : milliseconds based on 1970
        """
        if value is not None:
            splitVal = value.split('/')
            splitVal = [f'0{x}' if len(x) < 2 and int(x) <= 9 else x for x in splitVal]

            if len(splitVal) == 3 and len(splitVal[0]) <= 2 and len(splitVal[1]) <= 2 and len(splitVal[2]) <= 4:
                t = (parser().parse(value)-datetime(1970,1,1)).total_seconds()
                return "/".join(splitVal), t
        return value, None

    def convert_date(self, value, delimiter="/"):
        try:
            return datetime.strptime(value, f'%m{delimiter}%d{delimiter}%Y')
        except:
            return False
        
    def chkDatePattern(self, values):
        """
        This method checks a list of strings for potential date patterns and converts them to milliseconds.
        ### Parameters
        - values : list
            - A list of string values to check and convert, if possible
        ### Returns
        - Tuple with two values:
            - The first value is a list of string values that does not have proper date values.
            - The second is a list with converted date values.
        """
        dates = {}
        
        if type(values) == str:
            if 'sic' in values: return # SOME RECORDS MENTION THE VALUE IS WRONG
            return self.__chkDate(values)
        else:
            for value in values:
                try:

                    # MOST COMMON USE-CASE: DATE IS NUMERICAL IN NORMAL FORMAT
                    if any(char.isdigit() for char in value):

                        # IF THIS IS A FOUR-DIGIT VALUE ONLY WE ASSUME IT'S A YEAR
                        if all([char.isdigit() for char in value]) and len(value) == 4:
                            value = f'1/1/{value}'

                        try:

                            delimiter = Counter(list(self.regex.findall(value))).most_common(1)[0][0]
                            
                            date = self.convert_date(value, delimiter)

                            if date:
                                string, ms = self.__convertToMS(f'{date.month}/{date.day}/{date.year}')
                                dates[string] = str(ms)
                                continue
                            else:
                                
                                # SOMETHING IS WRONG WITH THE VALUE: PERHAPS A TYPO?
                                oldValue = value.split(delimiter)
                                newValue = []
                                for idx, val in enumerate(oldValue):
                                    newValue.append(val)
                                    if (len(val) == 2 or len(val) == 4): # WE ASSUME THE VALUES TO BE EITHER TWO OR FOUR CHARACTERS IN LENGTH
                                        for char in val:
                                            idx = val.index(char)
                                            if not char.isdigit():
                                                if char in self.__COMMONALPHATYPOS:
                                                    newValue[newValue.index(val)] = newValue[newValue.index(val)].replace(newValue[newValue.index(val)][val.index(char)], self.__COMMONALPHATYPOS[char])
                                    else:
                                        
                                        # IF THIS VALUE IS NOT ALPHANUMERIC
                                        if len(list(set([x for x in val if not x.isalnum() ]))):
                                            newValue[newValue.index(val)] = '01'

                                        # IF THIS VALUE IS LONGER THAN FOUR
                                        if len(val) > 4:

                                            # IF THE NUMBER IS A DIGIT AND STARTS WITH '19' or '20' IT'S LIKELY A YEAR
                                            if val.isdigit() and (val.startswith('19') or val.startswith('20')):

                                                # WE ASSUME THE LAST DIGIT IS WRONG
                                                newValue[newValue.index(val)] = val[:4]
                                            else:

                                                
                                                year = search(r'\d{4}', value).group(0)
                                                if year:
                                                    newValue[newValue.index(val)] = year

                                date = self.convert_date("/".join([val for val in newValue if val != '']), delimiter)
                                if date:
                                    string, ms = self.__convertToMS(f'{date.month}/{date.day}/{date.year}')
                                    dates[string] = str(ms)
                                    continue
                        except:
                            self.record_progress(dates)
                            return dates
                except:
                    raise
            
            self.record_progress(dates)
            return dates

    def record_progress(self, dates):
        self.current_date['dates'] = dates
        self.progress.append(self.current_date)

    def __chkDate(self, oldValue):
        """
        This method interprets a verbal description of a date pattern, matching month names against a global list
        ### Parameters
        - value : str,
            - String to deconstruct for comparison
        ### Returns
        - Tuple
            - Tuple with two values:
                - a bool indicating success or failure
                - a list of dictionaries with dates (keys) in milliseconds (value). This list is sorted ascending by dictionary values.
        """
        try:
            self.current_date = { 'val' : oldValue }
            if type(oldValue) == str:

            
                # NORMALIZE DIACRITICS
                oldValue = oldValue.replace('(', ';').replace(')', ';').replace('?', ';')
                date_values = oldValue.replace('-', ';').replace(':', ';').replace(',', ';').replace('//', ';').replace('[','').replace(']', '').split(';')
                date_values = [value.strip() for value in date_values]

                # CHECK IF ANY MONTH NAMES ARE MENTIONED AND REPLACE THESE WITH NUMBERS
                for idx, value in enumerate(date_values):
                    
                    if any([month for month in self.__MONTH.keys() if month in value.lower()]):

                        value = value.strip().lower()
                        
                        month = [month for month in self.__MONTH.keys() if month in value][0]

                        value = value.split(' ')
                        value.remove(month)

                        if len(value):
                            for val in value:
                                if val.isdigit():
                                    if len(val) == 4:
                                        day = '1' # NO DAY IN DATE
                                        year = val
                                    else:
                                        day = val
                                        if date_values[idx+1].isdigit() and len(date_values[idx+1]) == 4:
                                            year = date_values[idx+1].strip()
                                            date_values[idx+1] = ''
                        
                        # ONLY A MONTH IS MENTIONED IN THIS DATE
                        else:
                            # ASSUME A POTENTIAL YEAR FROM OTHER VALUES IN DATE_VALUES
                            day = '1'
                            year = search(r'\d{4}', oldValue).group(0)
                            
                        date_values[idx] = "/".join([self.__MONTH[month], day, year])

                    else:
                        words = findall(r"\b[a-zA-Z]+[a-zA-Z]\b", value)
                        if len(words):
                            value = value.split(' ')
                            value = [word for word in value if not word in words]
                            value = [val for val in value if len(val)]
                            date_values[idx] = " ".join(value) if len(value) else ""
                        else:
                            date_values[idx] = value.strip()

                newValue = " ".join([val for val in date_values if len(val)])

                if bool(self.regex.findall(newValue)):
                    date_values = newValue.split(' ') if len(newValue) > 10 else [newValue]

            if len(date_values) > 0:
                dates = self.chkDatePattern(date_values)

            sorted_dates = sorted(dates.items(), key=itemgetter(1))
            return sorted_dates
        except:
            raise ValueError(f'There was an error parsing the date string for "{value}"')