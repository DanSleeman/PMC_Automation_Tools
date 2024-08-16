class Error(Exception):
    pass
class PmcAutomationToolsError(Error):
    def __init__(self,*args,**kwargs):
        super().__init__(*args)
        for key, value in kwargs.items():
            setattr(self, key, value)
class PlexAutomateError(PmcAutomationToolsError):
    """A base class for handling exceptions in this project"""
    def __init__(self,*args,**kwargs):
        super().__init__(*args)
        for key, value in kwargs.items():
            setattr(self, key, value)
class NoRecordError(PlexAutomateError):
    """Thrown when no records exist in a picker selection."""
class ActionError(PlexAutomateError):
    """Thrown if there is an error on clicking an action bar item."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args)
        self.expression = kwargs.get('expression')
        self.message = kwargs.get('message')
class LoginError(PlexAutomateError):
    """Thrown if the expected login screens are not found."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args)
        self.environtment = kwargs.get('environment')
        self.db = kwargs.get('db')
        self.pcn = kwargs.get('pcn')
        self.message = kwargs.get('message')
class UpdateError(PlexAutomateError):
    """Thrown when a banner prevents an update from occurring."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args)
        self.clean_message = args[0].replace('×','').replace('\n','').strip()

class PlexApiError(PmcAutomationToolsError):
    """A base class for handling exceptions for API calls"""
class PlexResponseError(PlexApiError):...
class DataSourceError(PlexApiError):...
class ApiError(DataSourceError):...
class ClassicConnectionError(DataSourceError):...