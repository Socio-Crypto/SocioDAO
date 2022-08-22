from ast import Assert, Global, Return
import base64
from http import client

from algosdk.future import transaction
from algosdk import account, mnemonic, logic
from algosdk.v2client import algod
from pyteal import *
# from pyteal_helpers import program
import sys
from datetime import datetime


# user declared algod connection parameters. Node must have EnableDeveloperAPI set to true in its config
algod_add_c1ress = "https://testnet-algorand.api.purestake.io/ps2"
algod_token = "nJ5YXLrilW3yhWqFoMsV68CEcEJ54uAg1Z3XAFsN"
purestake_token = {'X-Api-key': algod_token}

#
#('bR08gDKo0McaGgDJJfew/Vs9O+L05YIrf3ostMWYYJBbB0VGHH9e98tcIHO46l8GmzyTtWp1yxqAcVpACqiVlA==', 'LMDUKRQ4P5PPPS24EBZ3R2S7A2NTZE5VNJ24WGUAOFNEACVISWKD7XRCYE')

# helper function to compile program source
def compile_program(client, source_code):
    compile_response = client.compile(source_code)
    return base64.b64decode(compile_response['result'])

# helper function that converts a mnemonic passphrase into a private signing key
def get_private_key_from_mnemonic(mn) :
    private_key = mnemonic.to_private_key(mn)
    return private_key

def wait_for_round(client, round):
    last_round = client.status().get("last-round")
    print(f"Waiting for round {round}")
    while last_round < round:
        last_round += 1
        client.status_after_block(last_round)
        print(f"Round {last_round}")


# helper function that formats global state for printing
def format_state(state):
    formatted = {}
    for item in state:
        key = item['key']
        value = item['value']
        formatted_key = base64.b64decode(key).decode('utf-8')
        if value['type'] == 1:
            # byte string
            if formatted_key == 'voted':
                formatted_value = base64.b64decode(value['bytes']).decode('utf-8')
            else:
                formatted_value = value['bytes']
            formatted[formatted_key] = formatted_value
        else:
            # integer
            formatted[formatted_key] = value['uint']
    return formatted

# helper function to read app global state
def read_global_state(client, app_id):
    app = client.application_info(app_id)
    global_state = app['params']['global-state'] if "global-state" in app['params'] else []
    return format_state(global_state)


"""Basic Choice1 Application in PyTeal"""

def approval_program():
    on_creation = Seq(
        [
            App.globalPut(Bytes("Creator"), Txn.sender()),
            Return(Int(1)),
        ]
    )

    is_creator = Txn.sender() == App.globalGet(Bytes("Creator"))

    #to be done
    on_closeout = Seq(
        [
            Return(Int(1)),
        ]
    )

    sender = Txn.application_args[1]
    balance_amount  = Txn.application_args[2]
    time_stamp = Txn.application_args[3]

    on_join = Seq(
        [   
            If(App.globalGet(sender), Return(Int(0))),
            If(Int(10)>Btoi(balance_amount), Return(Int(0))),
            App.globalPut(sender,Int(1)),
            Return(Int(1)),

        ]    
    )


    
    program1 = Cond(
        [Txn.application_id() == Int(0), on_creation],
        [Txn.on_completion() == OnComplete.DeleteApplication, Return(is_creator)],
        [Txn.on_completion() == OnComplete.UpdateApplication, Return(is_creator)],
        [Txn.on_completion() == OnComplete.CloseOut, on_closeout],
        [Txn.on_completion() == OnComplete.OptIn, Return(Int(1))],
        [Txn.application_args[0] == Bytes("join"), on_join],

    )

    # Mode.Application specifies that this is a smart contract
    return compileTeal(program1, Mode.Application, version=5)

def clear_state_program():
    program = Return(Int(1))
    # Mode.Application specifies that this is a smart contract
    return compileTeal(program, Mode.Application, version=5)


def create_app(
    client,
    private_key,
    approval_program,
    clear_program,
    global_schema,
    local_schema,
    # app_args,
):
    # define sender as creator
    sender = account.address_from_private_key(private_key)

    # declare on_complete as NoOp
    on_complete = transaction.OnComplete.NoOpOC.real

    # get node suggested parameters
    params = client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000

    # create unsigned transaction
    txn = transaction.ApplicationCreateTxn(
        sender,
        params,
        on_complete,
        approval_program,
        clear_program,
        global_schema,
        local_schema,
        # app_args,
    )

    # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    client.send_transactions([signed_txn])

    # confirmed_txn = transaction.wait_for_confirmation(client, tx_id, 4)

    # print("txID: {}".format(tx_id), " confirmed in round: {}".format(
    # confirmed_txn.get("confirmed-round", 0))) 


    # await confirmation
    transaction.wait_for_confirmation(client, tx_id)

    # display results
    transaction_response = client.pending_transaction_info(tx_id)
    app_id = transaction_response["application-index"]
    print("Created new app-id:", app_id)

    return app_id

# opt-in to application
def opt_in_app(client, private_key, index):
    # declare sender
    sender = account.address_from_private_key(private_key)
    print("OptIn from account: ", sender)

    # get node suggested parameters
    params = client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000
    app_args = []
    # create unsigned transaction
    txn = transaction.ApplicationOptInTxn(sender, params, index, app_args)

    # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    client.send_transactions([signed_txn])

    # await confirmation
    transaction.wait_for_confirmation(client, tx_id)

    # display results
    transaction_response = client.pending_transaction_info(tx_id)
    return transaction_response
# call application
def call_app(client, private_key, index, app_args):

    # declare sender
    sender = account.address_from_private_key(private_key)
    print("Call from account:", sender)

    # get node suggested parameters
    params = client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000
    #reciever 
    reciever = logic.get_application_address(index)
    # create unsigned transaction
    txn_1 = transaction.ApplicationNoOpTxn(sender, params, index, app_args)
    txn_2 = transaction.PaymentTxn(sender, params, reciever, 100000)

    group_id = transaction.calculate_group_id([txn_1, txn_2])

    txn_1.group = group_id
    txn_2.group = group_id

    stxn_1 = txn_1.sign(private_key)
    stxn_2 = txn_2.sign(private_key)

    signedGroup = []
    signedGroup.append(stxn_1)
    signedGroup.append(stxn_2)


    tx_id = client.send_transactions(signedGroup)

    # # sign transaction
    # signed_txn = txn.sign(private_key)
    # tx_id = signed_txn.transaction.get_txid()
    confirmed_txn = transaction.wait_for_confirmation(client, tx_id, 4)

    print("txID: {}".format(tx_id), " confirmed in round: {}".format(
    confirmed_txn.get("confirmed-round", 0))) 
    return tx_id

def propose_app(client, private_key, index, app_args):

    sender = account.address_from_private_key(private_key)
    print("Call from account:", sender)

    # get node suggested parameters
    params = client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000

    txn = transaction.ApplicationNoOpTxn(sender, params, index, app_args)

        # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    client.send_transactions([signed_txn])

    # await confirmation
    transaction.wait_for_confirmation(client, tx_id)

    # display results
    transaction_response = client.pending_transaction_info(tx_id)
    return transaction_response

def join_app(client, private_key, index, app_args):

    sender = account.address_from_private_key(private_key)
    print("Call from account:", sender)


    # get node suggested parameters
    params = client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000

    txn = transaction.ApplicationNoOpTxn(sender, params, index, app_args)

        # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    client.send_transactions([signed_txn])

    # await confirmation
    transaction.wait_for_confirmation(client, tx_id)

    # display results
    transaction_response = client.pending_transaction_info(tx_id)
    return transaction_response


def intToBytes(i):
    return i.to_bytes(8, "big")

def main(args) :

    # initialize an algodClient
    algod_client = algod.AlgodClient(algod_token, algod_add_c1ress, headers=purestake_token)

    if args[0] == 'create':
        # declare application state storage (immutable)
        # initialize an algodClient
        creator_private_key = get_private_key_from_mnemonic(args[1])

        # declare application state storage (immutable)
        local_ints = 1
        local_bytes = 2
        global_ints = (
            24  # 4 for setup + 20 for choices. Use a larger number for more choices.
        )
        global_bytes = 24
        global_schema = transaction.StateSchema(global_ints, global_bytes)
        local_schema = transaction.StateSchema(local_ints, local_bytes)

        #compile program to TEAL assembly
        with open("./approval.teal", "w") as f:
            approval_program_teal = approval_program()
            f.write(approval_program_teal)


        # compile program to TEAL assembly
        with open("./clear.teal", "w") as f:
            clear_state_program_teal = clear_state_program()
            f.write(clear_state_program_teal)
        
         # compile program to binary
        approval_program_compiled = compile_program(algod_client, approval_program_teal)

        # compile program to binary
        clear_state_program_compiled = compile_program(algod_client, clear_state_program_teal)

        print("--------------------------------------------")
        print("Deploying Voting application......")
        status = algod_client.status()
        regBegin = status["last-round"] + 10
        regEnd = regBegin + 5000
        voteBegin = status["last-round"]+ 10
        voteEnd = voteBegin + 5000


        print(f"Registration rounds: {regBegin} to {regEnd}")
        print(f"Vote rounds: {voteBegin} to {voteEnd}")

        # create list of bytes for app args
        # app_args = [
        #     intToBytes(regBegin),
        #     intToBytes(regEnd),
        #     intToBytes(voteBegin),
        #     intToBytes(voteEnd)
            
        # ]

        # create new application
        app_id = create_app(
            algod_client,
            creator_private_key,
            approval_program_compiled,
            clear_state_program_compiled,
            global_schema,
            local_schema,
            # app_args,
        )

        # create new application

        #read global state of application
        data = {'app_id':app_id}
        
        return app_id
    elif args[0] == 'join':
        sender_pc = get_private_key_from_mnemonic(args[2])
        address = account.address_from_private_key(sender_pc)
        data = algod_client.account_info(address)
        sender = address.encode('utf-8')
        amount = intToBytes(data['amount'])    
        time = datetime.now().strftime("%y:%m:%d %H:%M:%S").encode('utf-8')

        join_args = [b'join',sender, amount, time]

        return join_app(algod_client, sender_pc, args[1],join_args)
    elif args[1] == 'opt':
        # wait for registration period to start
        # wait_for_round(algod_client, regBegin)

        # opt-in to application
        return opt_in_app(algod_client, creator_private_key, args[2])

    elif args[1] == 'call':
        choice = args[1].encode('utf-8')
        amount = args[2]
        fund_choice = args[3].encode('utf-8')
        choice_state = args[4].encode('utf-8')
        choice_request = args[5].encode('utf-8')
        app_id = args[6]

        call_args = [
            b"vote",
            choice,
            intToBytes(amount),
            fund_choice,
            choice_state,
            choice_request
        ]

        return call_app(algod_client, creator_private_key, app_id, call_args)


    elif args[1] == 'propose':
        choice = args[1].encode('utf-8')
        fund_request = int(args[2])
        fund_request_text = args[3].encode('utf-8')
        choice_fund = args[4].encode('utf-8')
        choice_detail = args[5].encode('utf-8')
        choice_detail_text = args[6].encode('utf-8')
        choice_state = args[7].encode('utf-8')
        choice_owner = args[8].encode('utf-8')
        app_id = args[9]

        call_args = [
            b"propose",
            choice,
            intToBytes(fund_request),
            fund_request_text,
            choice_fund,
            choice_detail,
            choice_detail_text,
            choice_state,
            choice_owner
        ]

        return propose_app(algod_client, creator_private_key, app_id, call_args)



    elif args[0] =='read':
        return read_global_state(algod_client, args[1])

    else:
        app_id = args[3]
        print("--------------------------------------------")
        print("Calling Voting application......")
        app_args = [args[2]]
        call_app(algod_client, creator_private_key, app_id, app_args)

        # read global state of application
        print("Global state:", read_global_state(algod_client, app_id))

    
    

   

   