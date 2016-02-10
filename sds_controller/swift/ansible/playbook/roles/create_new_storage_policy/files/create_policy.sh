#!/bin/bash
#append into swift.conf the new policy

policyID=$1
policyName=$2
paritions=$3
replicas=$4
time=$5

IFS=',' read -r -a storage_nodes <<< "$6"

if [ $# -eq 6 ]
  then
    echo "[storage-policy:"$policyID"]
name = "$policyName >> /etc/swift/swift.conf
fi

if [ $# -eq 10 ]
  then
    echo "[storage-policy:"$policyID"]
name = "$policyName"
policy_type = erasure_coding
ec_type = "$7"
ec_num_data_fragments = "$8"
ec_num_parity_fragments = "$9"
ec_object_segment_size = "${10}"
" >> /etc/swift/swift.conf
fi

cd /etc/swift

swift-ring-builder object-$policyID\.builder create $paritions $replicas $time
#swift-ring-builder object-$policyID\.builder add $storage_node
for storage_node in "${storage_nodes[@]}"
do
    swift-ring-builder object-$policyID\.builder add $storage_node
done

swift-ring-builder object-$policyID\.builder rebalance
