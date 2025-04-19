Attacker_Addr = "0xa982444d884e00c7dfbbcb90e7a705e567853d0e"
Deployer_Addr = "0x8958c8689d325fd9e2a1ede3d5dc1acfcfb65742"

# 默认交易上下文
DEFAULT_TX_CTX = {
    "msg.sender": [Deployer_Addr, Attacker_Addr],
    "tx.origin": [Deployer_Addr, Attacker_Addr]
}

# 默认构造函数中的执行环境字段（部署者）由于不支持跨合约调用，默认sender和origin的值是相同的
DEFAULT_DEPLOYER_CTX = {
    "msg.sender": Deployer_Addr,
    "tx.origin": Deployer_Addr
}

# 默认被调用函数中的执行环境字段（攻击者）
DEFAULT_ATTACKER_CTX = {
    "msg.sender": Attacker_Addr,
    "tx.origin": Attacker_Addr
}
