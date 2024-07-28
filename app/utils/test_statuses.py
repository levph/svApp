# set status strings for each, including reset! (making other groups inactive)
statuses = [[1,1], [1,1]]

expecting = '0,1,3_0,1_3'

ptt_settings = []
for status in statuses:
    # classify each group
    listen = []
    talk = []
    monitor = []
    for ii, g in enumerate(status):
        if g == 1:
            listen.append(str(ii))
            talk.append(str(ii))
        elif g == 2:
            listen.append(str(ii))
            monitor.append(str(ii))

    listen = ','.join(listen)
    talk = ','.join(talk)
    monitor = ','.join(monitor)

    arr = [listen, talk, monitor] if monitor else [listen, talk]

    ptt_str = '_'.join(arr)
    ptt_settings.append([ptt_str])

print(f"Expecting: {expecting}")
print(f"We got: {ptt_settings}")