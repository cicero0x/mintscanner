# mintscanner

This is a simple tg bot I created in 2021 to ping me every time there are interesting nft mints.

TLDR of how the scanner works 

1. There is a list of notable addresses that I track. 

2. The bot leverages on etherscan apis to track what they are minting.

3. If 3 or more notable addresses are minting the same project, the bot will send a message on telegram with details of the nft collection pulled from opensea apis.

