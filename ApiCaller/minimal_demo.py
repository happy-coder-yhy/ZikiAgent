from modules.api_caller import APICallerConfig, ZataAPICaller

caller = ZataAPICaller(APICallerConfig(base_url="http://pre.zikirobo.com:30080/"))
caller.login(username="admin", password="1qaz@WSX1", organization="agent")

snapshot = caller.sync_platform_configuration(pageSize=200)