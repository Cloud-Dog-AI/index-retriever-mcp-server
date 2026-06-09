# CROSS-SERVICE FINDING (W28A-734-R2 estate sentinel sweep) — owner: COORDINATOR to dispatch

While running the §0B sentinel sweep, the SAME anonymous-admin /auth/me bypass
this lane fixed in index-retriever was observed LIVE on expert-agent:

  curl -k https://expertagent0.cloud-dog.net/auth/me   => HTTP 200  (anonymous principal returned)

Conforming siblings (correctly 401 unauth): sqlagent0, filemcpserver0, dbmcpserver0.

Root cause is the SAME class fixed here: the web tier's WebApiProxy injects the
service api_key on caller-identity proxy hops (/auth/me etc.). Recommend a
focused fix lane on expert-agent (and a full estate re-curl of /auth/me across
all 9 services) using the W28A-734-R2 pattern: forward verbatim for
/auth/*, /admin/*, /api/* (no injected service key); gate mcp/a2a injection on a
validated session. NOT caused by this lane; flagged per no-deferral rule.
