import requests

payload = {"apis":[{"method":"deferred_execution_api","params":{"version":"1","sleep":"1","api_list":[{"method":"save_node_labels_flash","params":["1",'"{\\"323285\\": \\"nadav\\", \\"324042\\": \\"lev6\\"}"']}]}}],"nodeids":[323285,324042],"override":1}
link = "http://172.20.241.202/bcast_enc.pyc"


res= requests.post(link,payload)
print(res)