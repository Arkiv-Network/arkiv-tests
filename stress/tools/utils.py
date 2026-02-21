import logging

def build_account_path(user_index: int) -> str:
    instance_index = 0
    logging.info(f"Building account path for user index {user_index} and instance index {instance_index}")
    return f"m/44'/60'/{instance_index}'/0/{user_index}"


# for instance_index in range(50):
#     for user_index in range(50):
#         path = f"m/44'/60'/{instance_index}'/0/{user_index}"
#         Account.enable_unaudited_hdwallet_features()
#         account: LocalAccount = Account.from_mnemonic(
#             "parent picture garment parrot churn record stadium pill rocket craft fish fiscal clip virus view diary replace wealth extra kitten door enforce piece nut", account_path=path
#         )
#         print("Account:", account.address)
