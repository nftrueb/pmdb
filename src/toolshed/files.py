import os 
import json 
from platformdirs import user_data_dir

class FatalFileException(Exception): 
    def __init__(self, message=None): 
        super().__init__(message or 'Fatal exception occurred in file layer')

class FileLayer: 
    def __init__(self): 
        self.initialized = False  
        self.appname = None

    def __str__(self): 
        return f'FileLayer:\nAppname: {self.appname}\nData dir: {user_data_dir(self.appname)}'
    
    def init(self, appname: str): 
        if appname is None: 
            raise FatalFileException('No appname provided to FileLayer')
        self.appname = appname

        self.init_data_dir(appname)

        self.initialized = True 

    def init_data_dir(self, appname: str): 
        data_path = user_data_dir(appname)
        if not os.path.exists(data_path): 
            os.mkdir(data_path)
            print(f'[INFO] Created data path: {data_path}')
    
    def check_initialized(self): 
        if not self.initialized: 
            raise FatalFileException('FileLayer is not yet initialized') 
        
    def data_file_exists(self, filename: str): 
        path = os.path.join(user_data_dir(self.appname), filename)
        return os.path.exists(path)
    
    def get_path(self, filename, use_data_dir): 
        return os.path.join(user_data_dir(self.appname), filename) if use_data_dir else filename
    
    def get_file_desc(self, filename, mode, use_data_dir): 
        return open(self.get_path(filename, use_data_dir), mode, encoding='utf-8')

    def load_text(self, filename: str, use_data_dir=True): 
        try: 
            f = self.get_file_desc(filename, 'r', use_data_dir)
            contents = f.read()
            f.close()
            return contents
        except Exception as ex: 
            raise FatalFileException(f'Failed to load text file: {filename}') from ex

    def load_bytes(self, filename: str, use_data_dir=True): 
        try: 
            f = self.get_file_desc(filename, 'rb', use_data_dir)
            contents = f.read()
            f.close()
            return contents
        except Exception as ex: 
            raise FatalFileException(f'Failed to load bytes file: {filename}') from ex

    def load_json(self, filename: str, use_data_dir=True): 
        try: 
            f = self.get_file_desc(filename, 'r', use_data_dir)
            contents = json.load(f)
            f.close()
            return contents
        except Exception as ex: 
            raise FatalFileException(f'Failed to load JSON file: {filename}') from ex
        
    def write_json(self, filename: str, data: dict, use_data_dir=True): 
        json_str = json.dumps(data, indent=4, sort_keys=True)
        f = self.get_file_desc(filename, 'w', use_data_dir)
        length = f.write(json_str)
        f.close()
        if length != len(json_str): 
            raise FatalFileException(f'Failed to write JSON data to file: {filename}')
            
    def write_text(self, filename: str, text: str, use_data_dir=True): 
        f = self.get_file_desc(filename, 'w', use_data_dir)
        length = f.write(text)
        f.close()
        if length != len(text): 
            raise FatalFileException(f'Failed to write text data to file: {filename}')
            
file_layer = FileLayer()

def get_file_layer(): 
    return file_layer
