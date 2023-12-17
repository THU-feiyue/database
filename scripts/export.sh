#!/bin/bash
wget 'https://cloud.seatable.io/api/v2.1/workspace/46522/synchronous-export/export-dtable/?dtable_name=THU%20feiyue' \
     --header 'accept: application/json' \
     --header "authorization: Bearer $SEAFILE_ACCOUNT_TOKEN" \
     --output-document 'feiyue.dtable'
