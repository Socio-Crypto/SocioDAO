from multiprocessing import context
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import Dao, Proposal
import base64
from algosdk import account, mnemonic, logic
from . import contract, members, voting_contract
from django.contrib import messages 

def init_dapp(request):
    daos = Dao.objects.all()
    context = {}
    context['daos'] = daos
    if request.method == 'POST':
        if request.POST['action'] == 'Create':
            mnemomic = request.POST['dao_creator']
            try:
                members_contract = members.main(['create',mnemomic])
            except Exception as e:
                messages.error(request, e)
                return redirect('/')
            try:
                voting_cntrct = voting_contract.main(['create', mnemomic, members_contract])
            except Exception as e:
                messages.error(request, e)
                return redirect('/')
            try:
                main_data = contract.main(['create', mnemomic, members_contract, voting_cntrct])
            except Exception as e:
                messages.error(request, e)
                return redirect('/')
            dapp = Dao()
            dapp.name = request.POST['dao_name']
            dapp.dao_id = main_data['app_id']
            dapp.save()
            string_data = 'App with app id ' + str(main_data['app_id']) + ' Created'
            messages.success(request, "Dao Created successfully" )

            return redirect('/dapp/'+str(main_data['app_id']))

    return render(request, 'create.html', context=context)


def call_dapp(request, dao_id):
    context = {}
    context['dao_id'] = dao_id
    users = {}
    global_data = contract.main(['read', dao_id])
    print(global_data)
    proposals = Proposal.objects.all()
    prps = {}

    for item in proposals:
        if dao_id == item.dao_id:
            coded = global_data[item.name+'detail']
            detail_string = base64.b64decode(coded).decode('utf-8')
            state_string = base64.b64decode(global_data[item.name+'state']).decode('utf-8')
            prps[item.name] = {'votes':global_data[item.name], 'fund_request':global_data[item.name+'request'],
             'fund_amount':global_data[item.name+'fund'], 'fund_detail':detail_string, 'fund_state': state_string,
             'fund_owner': global_data[item.name+'owner']}

    context['prps'] = prps
    voters = {}
    voting_id = global_data['voting_contract_id']
    global_data = contract.main(['read', voting_id])
    for item in proposals:
        if voting_id == item.dao_id:
            coded = global_data[item.name+'detail']
            detail_string = base64.b64decode(coded).decode('utf-8')
            voters[item.name] = {'votes':global_data[item.name], 
              'fund_detail':detail_string, 
             'fund_owner': global_data[item.name+'owner']}
            context['voters'] = voters

    members_id = global_data['members_contract_id']
    try:
        members_global = contract.main(['read',members_id])
    except Exception as e:
        messages.error(request, e)

    for i,j in members_global.items():
        if i != 'Creator':
            users[i] = j
    context['users'] = users
    print(context)

    if request.method == 'POST':
        if request.POST['action'] == 'join':
            pasphrase = request.POST['pasphrase']
            try:
                meta_data = members.main(['join', members_id, pasphrase ])
                return redirect('/dapp/'+str(dao_id))
            except Exception as e:
                messages.error(request, e)
    


    return render(request, 'actions.html', context=context)


def register_dapp(request, dao_id):
    # dapp = Dao.objects.get(dao_id=dao_id)
    # name = dapp.name
    # context = {'name':name, 'id':dao_id}
    # proposals = Proposal.objects.all()
    # prps = {}
    context = {}
    users = {}
    proposals = Proposal.objects.all()
    prps = {}
    global_data = contract.main(['read', dao_id])
    for item in proposals:
        if dao_id == item.dao_id:
            coded = global_data[item.name+'detail']
            detail_string = base64.b64decode(coded).decode('utf-8')
            state_string = base64.b64decode(global_data[item.name+'state']).decode('utf-8')
            prps[item.name] = {'votes':global_data[item.name], 'fund_request':global_data[item.name+'request'],
             'fund_amount':global_data[item.name+'fund'], 'fund_detail':detail_string, 'fund_state': state_string,
             'fund_owner': global_data[item.name+'owner']}
            context['prps'] = prps

    context['prps'] = prps
    
    print(context)
    members_id = global_data['members_contract_id']
    members_global = contract.main(['read',members_id])

    for i,j in members_global.items():
        if i != 'Creator':
            users[i] = base64.b64decode(j).decode('utf-8')
    context['users'] = users

    if request.method == 'POST':
        if request.POST['action'] == 'join':
            pasphrase = request.POST['pasphrase']
            try:
                meta_data = members.main(['join', members_id, pasphrase ])
                return redirect('/dapp/'+str(dao_id)+'/register')
            except Exception as e:
                return HttpResponse(e)
    

    return render(request, 'register.html', context=context)


def propose_dapp(request, dao_id):
    dapp = Dao.objects.get(dao_id=dao_id)
    name = dapp.name
    context = {'name':name, 'id':dao_id}
    proposals = Proposal.objects.all()
    prps = {}
    
    global_data = contract.main(['read', dao_id])
    for item in proposals:
        if dao_id == item.dao_id:
            coded = global_data[item.name+'detail']
            detail_string = base64.b64decode(coded).decode('utf-8')
            state_string = base64.b64decode(global_data[item.name+'state']).decode('utf-8')
            prps[item.name] = {'votes':global_data[item.name], 'fund_request':global_data[item.name+'request'],
             'fund_amount':global_data[item.name+'fund'], 'fund_detail':detail_string, 'fund_state': state_string,
             'fund_owner': global_data[item.name+'owner']}
            context['prps'] = prps

    context['prps'] = prps
    # context['data'] = global_data

    for i,j in global_data.items():
        context[i] = j

    address = base64.b32encode(base64.b64decode(context['Creator'])).decode('utf-8')[:32]
    context['address'] = address

    if request.method == 'POST':
        if request.POST['action'] == 'propose':
            sender = request.POST['pasphrase']
            proposal = request.POST['proposal_name']
            proposal_detail = request.POST['proposal_detail']
            fund_request = request.POST['fund_amount']
            proposal_fund_text = proposal + 'fund'
            proposal_detail_text = proposal + 'detail'
            proposal_request_text = proposal + 'request'
            proposal_state = proposal +'state'
            proposal_owner = proposal + 'owner'
            proposal_db = Proposal()
            proposal_db.dao_id = dao_id
            proposal_db.name = proposal

            args = [
                    'propose', proposal, fund_request,proposal_request_text, proposal_fund_text, proposal_detail,
                    proposal_detail_text,proposal_state, proposal_owner, dao_id, sender
                ]
            try:
                data = contract.main(args)
            except Exception as e:
                return HttpResponse(e)

            proposal_db.save()
            return redirect('/dapp/'+str(dao_id)+'/propose')

    return render(request, 'propose.html', context=context)


def crowdfund_dapp(request, dao_id):
    dapp = Dao.objects.get(dao_id=dao_id)
    name = dapp.name
    context = {'name':name, 'id':dao_id}
    proposals = Proposal.objects.all()
    prps = {}
    
    global_data = contract.main(['read', dao_id])
    for item in proposals:
        if dao_id == item.dao_id:
            coded = global_data[item.name+'detail']
            detail_string = base64.b64decode(coded).decode('utf-8')
            state_string = base64.b64decode(global_data[item.name+'state']).decode('utf-8')
            prps[item.name] = {'votes':global_data[item.name], 'fund_request':global_data[item.name+'request'],
             'fund_amount':global_data[item.name+'fund'], 'fund_detail':detail_string, 'fund_state': state_string,
             'fund_owner': global_data[item.name+'owner']}
            context['prps'] = prps
            
        
    

    context['prps'] = prps
    # context['data'] = global_data

    for i,j in global_data.items():
        context[i] = j

    address = base64.b32encode(base64.b64decode(context['Creator'])).decode('utf-8')[:32]
    context['address'] = address

    if request.method == 'POST':
        if request.POST['action'] == 'propose':
            try:
                sender = request.POST['pasphrase']
                proposal = request.POST['proposal_name']
                proposal_detail = request.POST['proposal_detail']
                fund_request = int(request.POST['fund_amount'])
                proposal_fund_text = proposal + 'fund'
                proposal_detail_text = proposal + 'detail'
                proposal_request_text = proposal + 'request'
                proposal_state = proposal +'state'
                proposal_owner = proposal + 'owner'
                proposal_db = Proposal()
                proposal_db.dao_id = dao_id
                proposal_db.name = proposal
            except Exception as e:
                messages.error(request, e)
                return redirect('/dapp/'+str(dao_id)+'/crowdfunding')

            args = [
                    'propose', proposal, fund_request,proposal_request_text, proposal_fund_text, proposal_detail,
                    proposal_detail_text,proposal_state, proposal_owner, dao_id, sender
                ]
            
            try:
                data = contract.main(args)
            except Exception as e:
                return messages.error(request, e)

            proposal_db.save()
            return redirect('/dapp/'+str(dao_id)+'/crowdfunding')

        elif request.POST['action'] == 'vote':
            try:
                sender = request.POST['pasphrase']
                choice = request.POST['choice']
                amount = int(request.POST['fund_amount'])
                proposal_fund_text = choice + 'fund'
                proposal_state = choice + 'state'
                proposal_request = choice + 'request'
            except Exception as e:
                messages.error(request, e)
                return redirect('/dapp/'+str(dao_id)+'/crowdfunding')
        
            args = ['call', choice, amount, proposal_fund_text,proposal_state ,proposal_request ,dao_id, sender]

            try:
                contract.main(['opt', sender, dao_id])
            except Exception as e:
                messages.error(request, e)
            try:
                meta_data = contract.main(args)
            except Exception as e:
                messages.error(request,e)

            return redirect('/dapp/'+str(dao_id)+'/crowdfunding')

    return render(request, 'crowdfunding.html', context=context)

def vote_dapp(request, dao_id):
    dapp = Dao.objects.get(dao_id=dao_id)
    name = dapp.name
    context = {'name':name, 'id':dao_id}
    proposals = Proposal.objects.all()
    prps = {}
    
    global_data = contract.main(['read', dao_id])
    print(global_data)
    voting_id = global_data['voting_contract_id']
    global_data = contract.main(['read', voting_id])
    print(global_data)

    for item in proposals:
        if voting_id == item.dao_id:
            coded = global_data[item.name+'detail']
            detail_string = base64.b64decode(coded).decode('utf-8')
            prps[item.name] = {'votes':global_data[item.name], 
              'fund_detail':detail_string, 
             'fund_owner': global_data[item.name+'owner']}
            context['prps'] = prps
            

    context['prps'] = prps
    # context['data'] = global_data
    print(prps)

    for i,j in global_data.items():
        context[i] = j

    address = base64.b32encode(base64.b64decode(context['Creator'])).decode('utf-8')[:32]
    context['address'] = address

    if request.method == 'POST':
        if request.POST['action'] == 'propose':
            sender = request.POST['pasphrase']
            proposal = request.POST['proposal_name']
            proposal_detail = request.POST['proposal_detail']
            proposal_detail_text = proposal + 'detail'
            proposal_owner = proposal + 'owner'
            proposal_db = Proposal()
            proposal_db.dao_id = voting_id
            proposal_db.name = proposal

            args = [
                    'propose', proposal,  proposal_detail,
                    proposal_detail_text, proposal_owner, voting_id, sender
                ]
            
            try:
                data = voting_contract.main(args)
            except Exception as e:
                messages.error(request, e)
                

            proposal_db.save()
            return redirect('/dapp/'+str(dao_id)+'/vote')

        elif request.POST['action'] == 'vote':
            sender = request.POST['pasphrase']
            choice = request.POST['choice']
        
            args = ['call', choice ,voting_id, sender]

            try:
                voting_contract.main(['opt', sender, voting_id])
            except Exception as e:
                messages.error(request, e)

            try:
                voting_contract.main(args)
            except Exception as e:
                messages.error(request, e)

            return redirect('/dapp/'+str(dao_id)+'/vote')

    return render(request, 'vote.html', context=context)


