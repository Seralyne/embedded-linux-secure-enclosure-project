Honestly, I think we're just gonna follow the suggested names from the build guide:

Topic                   Who Writes      Who reads
site/gateway-01/status  gateway         operator
site/gateway-01/alarm   gateway         operator
site/gateway-01/cmd     operator        gateway
site/node-01/health     ESP8266         operator
```

The gateway publishes compact JSON on the status topic:

```json
{"type":"STAT","counter":120,"door":0,"light":12,"relay":1,"state":"OK"}
```

It publishes alarms as JSON on the alarm topic:

```json
{"type":"ALRM","counter":121,"reason":"DOOR"}
```

To command the relay, publish JSON to the command topic. The gateway accepts
only `{"relay":0}` or `{"relay":1}`, validates it, and forwards the
corresponding checksummed `$CMD` message to the Pico:

```sh
mosquitto_pub -h localhost -t site/gateway-01/cmd -m '{"relay":1}'
```

The gateway audit log uses one plain-text line per event:

```text
time source event detail
```

For example:

```text
2026-11-13T01:10:00+0100 pico STAT $STAT,120,DOOR=0,LIGHT=012,RELAY=1,STATE=OK*67
2026-11-13T01:10:01+0100 mqtt CMD_ACCEPTED topic=site/gateway-01/cmd body=CMD,0,RELAY=1
```


