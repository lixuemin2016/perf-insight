### Azure Network Performance Testing

Microsoft Azure, formerly known as Windows Azure, is Microsoft's public cloud computing platform.

The Azure supports synthetic NIC and SR-IOV(ConnectX-3/ConnectX-4). Currently we only cover synthetic NIC performance test.  
For typical network performance test cases, we conduct TCP/UDP_STREAM, TCP/UDP_MAERTS, and TCP/UDP_RR tests with the pbench-uperf tool.  
Also, we offer "quick", "standard" and "extended" test dimension to meet different test requirements.

### Test dimension

| Dimension | Duration | test_types                | message_sizes    | protocols   | instances | samples | runtime |
| :-------- | :------- | :------------------------ | :--------------- | :---------- | :-------- | :------ | :------ |
| quick     | ~ 1h     | stream,maerts,bidirec,rr  | 1                | tcp,udp     | 1         | 3       | 20s     |
| standard  | ~ 6h     | stream,maerts,bidirec,rr  | 1,64             | tcp,udp     | 1,8       | 5       | 30s     |
| extended  | ~ 40h    | stream,maerts,bidirec,rr  | 1,64,1024,16384  | tcp,udp     | 1,8,64    | 5       | 60s     |

### Topologic

```
------------------------------------------------------
|  ------------------            ------------------  |
|  |  uperf client  |    link    |  uperf server  |  |
|  |      VM 1      |  <------>  |      VM 2      |  |
|  ------------------            ------------------  |
|                                                    |
|              Hypervisor - Azure Cloud              |
------------------------------------------------------
```

### Contact information

- IRC channel: #virt-pt @irc.devel.redhat.com  
- Mailing list: <virt-perftest@redhat.com>
- Product owner: Huijuan Zhao <huzhao@redhat.com>
