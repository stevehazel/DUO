from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal
import time

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder, ENCODERS_BY_TYPE
from fastapi import Header
from pydantic import BaseModel, Json
from typing import Any, Union
from pathlib import Path

ENCODERS_BY_TYPE[Decimal] = str

from util import emit_state_change
from config import config
from chain import get_chain, get_chains, init_chain
from blocks import BlockTypeMap, BlockType

service_name = config['service_name']

app = FastAPI()


@app.on_event('startup')
async def startup_event():
    current_state = get_current_state()
    emit_state_change(service_name, 'ServiceStarted', details=current_state)


@app.on_event('shutdown')
def shutdown_event():
    emit_state_change(service_name, 'ServiceStopped')


@app.get('/chain/{chain_uuid}/block/{block_hash}')
def chain_get_block_by_hash_GET(chain_uuid: UUID, block_hash: str):
    chain = get_chain(str(chain_uuid))
    block = chain.get_block_by_hash(block_hash)

    if block:
        return block.serialize()

    return {
        'found': False
    }


class AttrQuery(BaseModel):
    key: str
    subkey: Optional[str] = None
    value: Union[str, int, Decimal]
    value_type: str


class BlockQuery(BaseModel):
    block_type: Union[int, list]
    attr_query: Optional[AttrQuery] = None
    multiple: Optional[bool] = None
    window_far: Optional[int] = None
    window_near: Optional[int] = None


@app.post('/chain/{chain_uuid}/block/query')
def chain_block_query_POST(chain_uuid: UUID, block_query: BlockQuery):
    chain = get_chain(str(chain_uuid), cache_ttl=60)

    result = chain.block_query(
        block_query.block_type,
        attr_query=block_query.attr_query.dict() if block_query.attr_query else None,
        window_far=block_query.window_far,
        window_near=block_query.window_near,
        multiple=block_query.multiple,
    )

    if block_query.multiple:
        return [b.serialize() for b in result]
    elif result:
        return result.serialize()

    return {
        'found': False
    }


@app.get('/chains')
def chains_GET():
    chains = []

    import os
    chain_path = config['DUO_CHAIN_PATH']

    for chain in get_chains(chain_path=chain_path):
        head_block = chain.head_block()
        chains.append({
            'ID': chain.uuid,
            'BlockType': BlockTypeMap[head_block.block_type],
            'HeadHash': head_block.block_hash,
            'Balance': str(chain.balance()),
            'BlockHeight': head_block.height,
            'Blocks': [block.serialize() for block in chain.blocks]
        })

    return chains


@app.get('/chain/{chain_uuid}')
def chain_GET(chain_uuid: UUID):
    chain = get_chain(str(chain_uuid))
    head_block = chain.head_block()

    return {
        'ID': chain.uuid,
        'BlockType': BlockTypeMap[head_block.block_type],
        'HeadHash': head_block.block_hash,
        'Balance': str(chain.balance()),
        'BlockHeight': head_block.height,
        'Blocks': [block.serialize() for block in chain.blocks]
    }


@app.post('/chain')
def init_chain_POST():
    chain = init_chain()

    return {
        'uuid': chain.uuid
    }


@app.put('/chain/{chain_uuid}')
def init_chain_from_uuid_PUT(chain_uuid: UUID):
    chain = init_chain(str(chain_uuid))

    return {
        'uuid': chain.uuid
    }


@app.get('/chain/{chain_uuid}/credibility')
def read_chain_credibility(chain_uuid: UUID):
    chain = get_chain(str(chain_uuid))
    credibility_stats = chain.get_credibility(minimal=True)

    return {
        'stats': credibility_stats
    }


@app.get('/chain/{chain_uuid}/credibility/{other_chain_uuid}')
def read_chain_credibility_other(chain_uuid: UUID, other_chain_uuid: UUID):
    chain = get_chain(str(chain_uuid))
    other_chain_uuid = str(other_chain_uuid)
    credibility_stats = chain.get_credibility(other_chain_uuid, minimal=True)

    return {
        'other_chain_uuid': other_chain_uuid,
        'stats': credibility_stats[other_chain_uuid]
    }


@app.get('/chain/{chain_uuid}/balance')
def read_chain_balance(chain_uuid: UUID):
    chain = get_chain(str(chain_uuid))

    return {
        'balance': str(chain.balance())
    }


@app.get('/chain/{chain_uuid}/verify')
def chain_verify_GET(chain_uuid: UUID):
    success = False
    error_message = None
    try:
        chain = get_chain(str(chain_uuid))
        result = chain.verify()
    except Exception as e:
        success = False
        error_message = str(e)
        import traceback ; traceback.print_exc()
    else:
        success = True

    return {
        'Success': success,
        'ErrorMessage': error_message
    }


@app.post('/chain/{chain_uuid}/make_valid')
def chain_block_make_valid_POST(chain_uuid: UUID):
    success = False
    error_message = None

    chain = get_chain(str(chain_uuid))

    try:
        result = chain.make_valid()
    except Exception as e:
        success = False
        error_message = str(e)
        import traceback ; traceback.print_exc()
    else:
        if result and chain.verify(exc=False) is True:
            chain.save()
            success = True
        else:
            error_message = 'Chain could not be made valid'

    return {
        'Success': success,
        'ErrorMessage': error_message
    }


class UpdateBlock(BaseModel):
    block: Json


@app.post('/chain/{chain_uuid}/block/{block_hash}/update')
def chain_block_update_POST(chain_uuid: UUID, block_hash: str, update_block: UpdateBlock):
    success = False
    error_message = None

    chain = get_chain(str(chain_uuid))

    try:
        update_block_hash = update_block.block['block_hash']
        block_idx = chain.get_block_idx_by_hash(update_block_hash)
        if block_idx >= 0:
            block = chain.blocks[block_idx]
            block.update(**update_block.block)
            chain.save()

    except Exception as e:
        success = False
        error_message = str(e)
        import traceback ; traceback.print_exc()
    else:
        success = True

    return {
        'Success': success,
        'ErrorMessage': error_message
    }


@app.post('/chain/{chain_uuid}/delete')
def chain_delete_POST(chain_uuid: UUID):
    chain = get_chain(str(chain_uuid))
    chain.delete()

    return {
        'Success': True,
    }


class DeleteBlock(BaseModel):
    block: Json


@app.post('/chain/{chain_uuid}/block/{block_hash}/delete')
def chain_block_delete_POST(chain_uuid: UUID, block_hash: str, delete_block: DeleteBlock):
    success = False
    error_message = None

    chain = get_chain(str(chain_uuid))

    try:
        delete_block_hash = delete_block.block['block_hash']
        block_idx = chain.get_block_idx_by_hash(delete_block_hash)
        if block_idx >= 0:
            del chain.blocks[block_idx]

        chain.save()

    except Exception as e:
        success = False
        error_message = str(e)
        import traceback ; traceback.print_exc()
    else:
        success = True

    return {
        'Success': success,
        'ErrorMessage': error_message
    }


@app.get('/chain/{chain_uuid}/cross_verify/{other_chain_uuid}')
def chain_cross_verify_GET(chain_uuid: UUID, other_chain_uuid: UUID):
    success = False
    error_message = None
    try:
        cross_verify(chain_uuid, other_chain_uuid)
    except Exception as e:
        success = False
        error_message = str(e)
    else:
        success = True

    return {
        'Success': success,
        'ErrorMessage': error_message
    }


@app.get('/chain/{chain_uuid}/hard_verify/{other_chain_uuid}')
def chain_hard_verify_GET(chain_uuid: UUID, other_chain_uuid: UUID):
    success = False
    error_message = None
    try:
        cross_verify(chain_uuid, other_chain_uuid)

        chain = get_chain(str(chain_uuid))
        other_chain = get_chain(str(other_chain_uuid))

        chain.hard_verify(other_chain)
        other_chain.hard_verify(chain)
    except Exception as e:
        success = False
        error_message = str(e)
    else:
        success = True

    return {
        'Success': success,
        'ErrorMessage': error_message
    }


def cross_verify(chain_uuid, other_chain_uuid):
    chain = get_chain(str(chain_uuid))
    other_chain = get_chain(str(other_chain_uuid))

    # First make sure that both chains are individually valid.
    # Doing this first simplifies the cross-verification.
    chain.verify()
    other_chain.verify()

    # Then make sure that each chain corroborates the other.
    chain.cross_verify(other_chain)
    other_chain.cross_verify(chain)

    return True



class QueryReceivedSignals(BaseModel):
    activity_uuid: UUID
    epoch_from: int
    epoch_to: int


@app.post('/chain/{chain_uuid}/query_received_signals')
def query_received_signals_POST(chain_uuid: UUID, query_received_signals: QueryReceivedSignals):
    success = False
    error_message = None

    activity_uuid = str(query_received_signals.activity_uuid)
    epoch_from_ms = query_received_signals.epoch_from * 1000
    epoch_to_ms = query_received_signals.epoch_to * 1000

    chain = get_chain(str(chain_uuid))

    signals = []
    try:
        for block in chain.blocks:
            # Do blocks even have timestamps?
            #   uhhh...

            if block.block_type not in (BlockType.SignalDelivered, ):
                continue

            ts = int(block.ts)

            if ts < epoch_from_ms:
                continue

            if ts > epoch_to_ms:
                continue

            if block.activity_id != activity_uuid:
                continue

            signals.append({
                'block_hash': block.block_hash,
                'ts': ts,
                'cost': block.cost,
                'source_chain_uuid': block.src_chain_id
            })

        signals.sort(key=lambda x: x['ts'], reverse=False)

    except Exception as e:
        success = False
        error_message = str(e)
        import traceback ; traceback.print_exc()
    else:
        success = True

    return {
        'Success': success,
        'ErrorMessage': error_message,
        'signals': signals
    }


class SendSignal(BaseModel):
    other_chain_uuid: UUID
    signal_data: dict
    reward_amount: Optional[Decimal] = None
    debit: Optional[bool] = None


@app.post('/chain/{chain_uuid}/block/send_signal')
def create_block__send_signal(chain_uuid: UUID, send_signal: SendSignal):
    chain_uuid = str(chain_uuid)
    other_chain_uuid = str(send_signal.other_chain_uuid)
    signal_data = send_signal.signal_data
    reward_amount = send_signal.reward_amount

    # Enforce a minimum amount
    if reward_amount and reward_amount < 1.00:
        reward_amount = None

    chain = get_chain(chain_uuid)
    send_signal_block = chain.send_signal(
        other_chain_uuid,
        signal_data,
        amount=reward_amount
    )
    prev_block_hash = send_signal_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'SendSignal',
        'OnChainID': chain_uuid,
        'OtherChainID': other_chain_uuid,
        'BlockHash': send_signal_block.block_hash,
        'PrevBlockHash': prev_block_hash,
        'Signal': send_signal.signal_data,
        'SerializedBlock': send_signal_block.serialize(),
        'RewardAmount': reward_amount,
        #'SerializedDebitBlock': debit_block.serialize() if debit_block else None,
    })

    debit_block = None
    if send_signal.debit and reward_amount:
        ref_block_hash = send_signal_block.block_hash
        debit_block = chain.debit(
            reward_amount,
            ref_block_hash=ref_block_hash
        )
        prev_block_hash = debit_block.prev_block_hash

        emit_state_change(service_name, 'BlockAdded', {
            'BlockType': 'Debit',
            'OnChainID': chain_uuid,
            'Amount': str(reward_amount),
            'RefBlockHash': ref_block_hash,
            'BlockHash': debit_block.block_hash,
            'PrevBlockHash': prev_block_hash,
            'Balance': str(debit_block.balance),
            'BalanceDelta': str(debit_block.balance_delta),
            'SerializedBlock': debit_block.serialize()
        })

    return {
        'send_signal_block_hash': send_signal_block.block_hash,
    }


class ReceiveSignal(BaseModel):
    other_chain_uuid: UUID
    send_signal_block_hash: str
    signal_data: dict
    amount: Optional[Decimal] = None
    details: Optional[dict] = None


@app.post('/chain/{chain_uuid}/block/receive_signal')
def create_block__receive_signal(chain_uuid: UUID, receive_signal: ReceiveSignal):
    chain_uuid = str(chain_uuid)
    other_chain_uuid = str(receive_signal.other_chain_uuid)
    send_signal_block_hash = receive_signal.send_signal_block_hash
    signal_data = receive_signal.signal_data
    amount = receive_signal.amount

    chain = get_chain(chain_uuid)
    receive_signal_block = chain.receive_signal(
        other_chain_uuid,
        send_signal_block_hash,
        signal_data,
        amount=amount,
        details=receive_signal.details
    )
    prev_block_hash = receive_signal_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'ReceiveSignal',
        'OnChainID': chain_uuid,
        'OtherChainID': other_chain_uuid,
        'Amount': str(amount),
        'Signal': signal_data,
        'RefBlockHash': send_signal_block_hash,
        'BlockHash': receive_signal_block.block_hash,
        'PrevBlockHash': prev_block_hash,
        'SerializedBlock': receive_signal_block.serialize()
    })

    return {
        'receive_signal_block_hash': receive_signal_block.block_hash,
    }


class DeliverSignal(BaseModel):
    other_chain_uuid: UUID
    receive_signal_block_hash: str
    activity_uuid: UUID
    cost: int
    amount: Optional[Decimal] = None


@app.post('/chain/{chain_uuid}/block/deliver_signal')
def create_block__deliver_signal(chain_uuid: UUID, deliver_signal: DeliverSignal):
    chain_uuid = str(chain_uuid)
    other_chain_uuid = str(deliver_signal.other_chain_uuid)
    activity_uuid = str(deliver_signal.activity_uuid)
    receive_signal_block_hash = deliver_signal.receive_signal_block_hash
    cost = deliver_signal.cost
    amount = deliver_signal.amount

    chain = get_chain(chain_uuid)
    deliver_signal_block = chain.deliver_signal(
        other_chain_uuid,
        receive_signal_block_hash,
        activity_uuid,
        cost=cost,
        amount=amount
    )
    prev_block_hash = deliver_signal_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'DeliverSignal',
        'OnChainID': chain_uuid,
        'OtherChainID': other_chain_uuid,
        'Cost': cost,
        'Amount': str(amount),
        'RefBlockHash': receive_signal_block_hash,
        'BlockHash': deliver_signal_block.block_hash,
        'PrevBlockHash': prev_block_hash,
        'SerializedBlock': deliver_signal_block.serialize()
    })

    return {
        'deliver_signal_block_hash': deliver_signal_block.block_hash,
    }


class SendSignalReward(BaseModel):
    other_chain_uuid: UUID
    deliver_signal_block_hash: str
    action_block_hash: str
    amount: Decimal
    accepted_amount: Optional[Decimal] = None


@app.post('/chain/{chain_uuid}/block/send_signal_reward')
def create_block__send_signal_reward(chain_uuid: UUID, send_signal_reward: SendSignalReward):
    chain_uuid = str(chain_uuid)
    other_chain_uuid = str(send_signal_reward.other_chain_uuid)
    deliver_signal_block_hash = send_signal_reward.deliver_signal_block_hash
    action_block_hash = send_signal_reward.action_block_hash
    amount = Decimal(send_signal_reward.amount)
    accepted_amount = Decimal(send_signal_reward.accepted_amount)

    chain = get_chain(chain_uuid)
    send_signal_reward_block = chain.send_signal_reward(
        other_chain_uuid,
        action_block_hash,
        deliver_signal_block_hash,
        amount,
        accepted_amount=accepted_amount
    )
    prev_block_hash = send_signal_reward_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'SendSignalReward',
        'OnChainID': chain_uuid,
        'OtherChainID': other_chain_uuid,
        'Amount': str(amount),
        'RefBlockHash': deliver_signal_block_hash,
        'BlockHash': send_signal_reward_block.block_hash,
        'PrevBlockHash': prev_block_hash,
        'SerializedBlock': send_signal_reward_block.serialize()
    })

    return {
        'send_signal_reward_block_hash': send_signal_reward_block.block_hash,
    }


class ReceiveSignalReward(BaseModel):
    other_chain_uuid: UUID
    send_signal_reward_block_hash: str
    amount: Decimal


@app.post('/chain/{chain_uuid}/block/receive_signal_reward')
def create_block__receive_signal_reward(chain_uuid: UUID, receive_signal_reward: ReceiveSignalReward):
    chain_uuid = str(chain_uuid)
    other_chain_uuid = str(receive_signal_reward.other_chain_uuid)
    send_signal_reward_block_hash = receive_signal_reward.send_signal_reward_block_hash
    amount = Decimal(receive_signal_reward.amount)

    chain = get_chain(chain_uuid)

    receive_signal_reward_block = chain.receive_signal_reward(
        other_chain_uuid,
        send_signal_reward_block_hash,
        amount
    )
    prev_block_hash = receive_signal_reward_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'ReceiveSignalReward',
        'OnChainID': chain_uuid,
        'OtherChainID': other_chain_uuid,
        'Amount': str(amount),
        'RefBlockHash': send_signal_reward_block_hash,
        'BlockHash': receive_signal_reward_block.block_hash,
        'PrevBlockHash': prev_block_hash,
        'Balance': str(receive_signal_reward_block.balance),
        'BalanceDelta': str(receive_signal_reward_block.balance_delta),
        'SerializedBlock': receive_signal_reward_block.serialize()
    })

    return {
        'receive_signal_reward_block_hash': receive_signal_reward_block.block_hash,
    }


class AddTarget(BaseModel):
    name: str
    reward_per: Decimal
    reward_pool: Decimal
    priors: Optional[list] = None
    conditions: Optional[list] = None
    target_uuid: Optional[UUID] = None


@app.post('/chain/{chain_uuid}/block/target')
def create_block__target(chain_uuid: UUID, new_target: AddTarget):
    chain_uuid = str(chain_uuid)

    name = new_target.name
    reward_per = new_target.reward_per
    reward_pool = new_target.reward_pool
    priors = new_target.priors
    conditions = new_target.conditions
    target_uuid = new_target.target_uuid

    if not target_uuid:
        target_uuid = str(uuid4())

    chain = get_chain(chain_uuid)

    target_block = chain.add_target(
        name,
        target_uuid,
        reward_per,
        reward_pool,
        priors=priors,
        conditions=conditions
    )
    prev_block_hash = target_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'Target',
        'OnChainID': chain_uuid,
        'Name': name,
        'TargetID': target_uuid,
        'RewardPer': str(reward_per),
        'RewardPool': str(reward_pool),
        'Priors': priors,
        'Conditions': conditions,
        'BlockHash': target_block.block_hash,
        'PrevBlockHash': prev_block_hash,
        'Balance': str(target_block.balance),
        'BalanceDelta': str(target_block.balance_delta),
        'SerializedBlock': target_block.serialize()
    })

    return {
        'target_block_hash': target_block.block_hash,
        'target_uuid': target_uuid
    }


class AcceptTarget(BaseModel):
    target_src_chain_uuid: UUID
    name: str
    #action_block_hash: str
    target_block_hash: str
    target_uuid: UUID
    target_details: dict


@app.post('/chain/{chain_uuid}/block/accept_target')
def create_block__accept_target(chain_uuid: UUID, accepted_target: AcceptTarget):
    chain_uuid = str(chain_uuid)

    target_src_chain_uuid = str(accepted_target.target_src_chain_uuid)
    name = accepted_target.name
    #action_block_hash = accepted_target.action_block_hash
    target_uuid = str(accepted_target.target_uuid)
    target_block_hash = accepted_target.target_block_hash
    target_details = accepted_target.target_details

    chain = get_chain(chain_uuid)

    accept_target_block = chain.accept_target(
        target_src_chain_uuid,
        #action_block_hash,
        target_uuid,
        target_block_hash,
        target_details
    )
    prev_block_hash = accept_target_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'TargetAccepted',
        'OnChainID': chain_uuid,
        'TargetSourceChainID': target_src_chain_uuid,
        'Name': name,
        'TargetID': target_uuid,
        'Details': target_uuid,
        'BlockHash': accept_target_block.block_hash,
        'PrevBlockHash': prev_block_hash,
        'Balance': str(accept_target_block.balance),
        'BalanceDelta': str(accept_target_block.balance_delta),
        'SerializedBlock': accept_target_block.serialize()
    })

    return {
        'accept_target_block_hash': accept_target_block.block_hash,
    }


class AddAction(BaseModel):
    action_uuid: UUID
    activity_uuid: UUID
    activity_refs: Optional[dict] = None
    deliver_signal_block_hash: Optional[str] = None


@app.post('/chain/{chain_uuid}/block/action')
def create_block__action(chain_uuid: UUID, new_action: AddAction):
    chain_uuid = str(chain_uuid)
    action_uuid = str(new_action.action_uuid)
    activity_uuid = str(new_action.activity_uuid)

    activity_refs = new_action.activity_refs
    if not activity_refs:
        activity_refs = {
            'up': [],
            'down': [],
            'other': []
        }

    chain = get_chain(chain_uuid)
    action_block = chain.add_action(
        action_uuid,
        activity_uuid,
        activity_refs,
        deliver_signal_block_hash=new_action.deliver_signal_block_hash
    )
    prev_block_hash = action_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'Action',
        'OnChainID': chain_uuid,
        'ActivityID': activity_uuid,
        'ActionID': action_uuid,
        'ActivityRefs': activity_refs,
        'BlockHash': action_block.block_hash,
        'RefBlockHash': new_action.deliver_signal_block_hash,
        'PrevBlockHash': prev_block_hash,
        'Balance': str(action_block.balance),
        'BalanceDelta': str(action_block.balance_delta),
        'SerializedBlock': action_block.serialize()
    })

    return {
        'action_block_hash': action_block.block_hash,
    }


class AddWorkOutput(BaseModel):
    action_uuid: UUID
    activity_uuid: UUID
    activity_refs: Optional[dict] = None
    work_output_details: Optional[dict] = None


@app.post('/chain/{chain_uuid}/block/work_output')
def create_block__work_output(chain_uuid: UUID, new_work_output: AddWorkOutput):
    chain_uuid = str(chain_uuid)
    action_uuid = str(new_work_output.action_uuid)
    activity_uuid = str(new_work_output.activity_uuid)

    activity_refs = new_work_output.activity_refs
    if not activity_refs:
        activity_refs = {
            'up': [],
            'down': [],
            'other': []
        }

    details = new_work_output.work_output_details
    if not details:
        details = {}

    chain = get_chain(chain_uuid)
    work_output_block = chain.add_work_output(
        action_uuid,
        activity_uuid,
        activity_refs,
        details=details
    )
    prev_block_hash = work_output_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'WorkOutput',
        'OnChainID': chain_uuid,
        'ActivityID': activity_uuid,
        'ActionID': action_uuid,
        'ActivityRefs': activity_refs,
        'Details': details,
        'BlockHash': work_output_block.block_hash,
        'PrevBlockHash': prev_block_hash,
        'Balance': str(work_output_block.balance),
        'BalanceDelta': str(work_output_block.balance_delta),
        'SerializedBlock': work_output_block.serialize()
    })

    return {
        'work_output_block_hash': work_output_block.block_hash,
    }


class AddSendTargetRewardClaim(BaseModel):
    target_src_chain_uuid: UUID
    target_block_hash: str
    work_output_block_hash: str
    work_output_details: Optional[dict] = None


@app.post('/chain/{chain_uuid}/block/send_target_reward_claim')
def create_block__send_target_reward_claim(chain_uuid: UUID, new_reward_claim: AddSendTargetRewardClaim):
    chain_uuid = str(chain_uuid)
    target_src_chain_uuid = str(new_reward_claim.target_src_chain_uuid)
    target_block_hash = new_reward_claim.target_block_hash
    work_output_block_hash = new_reward_claim.work_output_block_hash

    work_output_details = new_reward_claim.work_output_details
    if not work_output_details:
        work_output_details = {}

    chain = get_chain(chain_uuid)
    send_target_reward_claim_block = chain.send_target_reward_claim(
        target_src_chain_uuid,
        target_block_hash,
        work_output_block_hash,
        work_output_details
    )
    prev_block_hash = send_target_reward_claim_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'TargetRewardClaimSent',
        'OnChainID': chain_uuid,
        'TargetSrcChainID': target_src_chain_uuid,
        'TargetBlockHash': target_block_hash,
        'WorkOutputBlockHash': work_output_block_hash,
        'WorkOutputDetails': work_output_details,
        'BlockHash': send_target_reward_claim_block.block_hash,
        'PrevBlockHash': prev_block_hash,
        'Balance': str(send_target_reward_claim_block.balance),
        'BalanceDelta': str(send_target_reward_claim_block.balance_delta),
        'SerializedBlock': send_target_reward_claim_block.serialize()
    })

    return {
        'send_target_reward_claim_block_hash': send_target_reward_claim_block.block_hash,
    }


class AddReceiveTargetRewardClaim(BaseModel):
    claim_src_chain_uuid: UUID
    send_target_reward_claim_block_hash: str
    target_block_hash: str
    work_output_block_hash: str
    work_output_details: Optional[dict] = None


@app.post('/chain/{chain_uuid}/block/receive_target_reward_claim')
def create_block__receive_target_reward_claim(chain_uuid: UUID, new_reward_claim: AddReceiveTargetRewardClaim):
    chain_uuid = str(chain_uuid)
    claim_src_chain_uuid = str(new_reward_claim.claim_src_chain_uuid)
    target_block_hash = new_reward_claim.target_block_hash
    send_target_reward_claim_block_hash = new_reward_claim.send_target_reward_claim_block_hash
    work_output_block_hash = new_reward_claim.work_output_block_hash

    work_output_details = new_reward_claim.work_output_details
    if not work_output_details:
        work_output_details = {}

    chain = get_chain(chain_uuid)
    receive_target_reward_claim_block = chain.receive_target_reward_claim(
        claim_src_chain_uuid,
        target_block_hash,
        send_target_reward_claim_block_hash,
        work_output_block_hash,
        work_output_details
    )
    prev_block_hash = receive_target_reward_claim_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'TargetRewardClaimSent',
        'OnChainID': chain_uuid,
        'SrcChainID': claim_src_chain_uuid,
        'SendTargetRewardClaimBlockHash': send_target_reward_claim_block_hash,
        'TargetBlockHash': target_block_hash,
        'WorkOutputBlockHash': work_output_block_hash,
        'WorkOutputDetails': work_output_details,
        'BlockHash': receive_target_reward_claim_block.block_hash,
        'PrevBlockHash': prev_block_hash,
        'Balance': str(receive_target_reward_claim_block.balance),
        'BalanceDelta': str(receive_target_reward_claim_block.balance_delta),
        'SerializedBlock': receive_target_reward_claim_block.serialize()
    })

    return {
        'receive_target_reward_claim_block_hash': receive_target_reward_claim_block.block_hash,
    }


class AddSendTargetReward(BaseModel):
    claim_src_chain_uuid: UUID
    target_block_hash: str
    receive_target_reward_claim_block_hash: str
    reward_amount: Decimal


@app.post('/chain/{chain_uuid}/block/send_target_reward')
def create_block__send_target_reward(chain_uuid: UUID, new_reward: AddSendTargetReward):
    chain_uuid = str(chain_uuid)
    claim_src_chain_uuid = str(new_reward.claim_src_chain_uuid)
    receive_target_reward_claim_block_hash = new_reward.receive_target_reward_claim_block_hash
    target_block_hash = new_reward.target_block_hash
    reward_amount = new_reward.reward_amount

    chain = get_chain(chain_uuid)

    send_target_reward_block = chain.send_target_reward(
        claim_src_chain_uuid,
        target_block_hash,
        receive_target_reward_claim_block_hash,
        reward_amount,
    )
    prev_block_hash = send_target_reward_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'TargetRewardSent',
        'OnChainID': chain_uuid,
        'RewardAmount': str(reward_amount),
        'ClaimSrcChainID': claim_src_chain_uuid,
        'TargetBlockHash': target_block_hash,
        'ReceiveTargetRewardClaimBlockHash': receive_target_reward_claim_block_hash,
        'BlockHash': send_target_reward_block.block_hash,
        'PrevBlockHash': prev_block_hash,
        'Balance': str(send_target_reward_block.balance),
        'BalanceDelta': str(send_target_reward_block.balance_delta),
        'SerializedBlock': send_target_reward_block.serialize()
    })

    return {
        'send_target_reward_block_hash': send_target_reward_block.block_hash,
    }


class AddReceiveTargetReward(BaseModel):
    target_src_chain_uuid: UUID
    target_block_hash: str
    send_target_reward_block_hash: str
    reward_amount: Decimal


@app.post('/chain/{chain_uuid}/block/receive_target_reward')
def create_block__receive_target_reward(chain_uuid: UUID, new_reward: AddReceiveTargetReward):
    chain_uuid = str(chain_uuid)
    target_src_chain_uuid = str(new_reward.target_src_chain_uuid)
    send_target_reward_block_hash = new_reward.send_target_reward_block_hash
    target_block_hash = new_reward.target_block_hash
    reward_amount = new_reward.reward_amount

    chain = get_chain(chain_uuid)
    receive_target_reward_block = chain.receive_target_reward(
        target_src_chain_uuid,
        target_block_hash,
        send_target_reward_block_hash,
        reward_amount,
    )
    prev_block_hash = receive_target_reward_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'TargetRewardReceived',
        'OnChainID': chain_uuid,
        'RewardAmount': str(reward_amount),
        'TargetSrcChainID': target_src_chain_uuid,
        'TargetBlockHash': target_block_hash,
        'SendTargetRewardBlockHash': send_target_reward_block_hash,
        'BlockHash': receive_target_reward_block.block_hash,
        'PrevBlockHash': prev_block_hash,
        'Balance': str(receive_target_reward_block.balance),
        'BalanceDelta': str(receive_target_reward_block.balance_delta),
        'SerializedBlock': receive_target_reward_block.serialize()
    })

    return {
        'receive_target_reward_block_hash': receive_target_reward_block.block_hash,
    }


class AddDebit(BaseModel):
    amount: Decimal
    ref_block_hash: Optional[str] = None


@app.post('/chain/{chain_uuid}/block/debit')
def create_block__debit(chain_uuid: UUID, new_debit: AddDebit):
    chain_uuid = str(chain_uuid)

    ref_block_hash = new_debit.ref_block_hash
    if not ref_block_hash:
        ref_block_hash = ''

    chain = get_chain(chain_uuid)
    debit_block = chain.debit(
        new_debit.amount,
        ref_block_hash=ref_block_hash
    )
    prev_block_hash = debit_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'Debit',
        'OnChainID': chain_uuid,
        'Amount': str(new_debit.amount),
        'RefBlockHash': ref_block_hash,
        'BlockHash': debit_block.block_hash,
        'PrevBlockHash': prev_block_hash,
        'Balance': str(debit_block.balance),
        'BalanceDelta': str(debit_block.balance_delta),
        'SerializedBlock': debit_block.serialize()
    })

    return {
        'debit_block_hash': debit_block.block_hash,
    }


class AcceptCredit(BaseModel):
    amount: Decimal
    ref_block_hash: Optional[str] = None


@app.post('/chain/{chain_uuid}/block/accept_credit')
def create_block__debit(chain_uuid: UUID, new_credit: AcceptCredit):
    chain_uuid = str(chain_uuid)

    ref_block_hash = new_credit.ref_block_hash
    if not ref_block_hash:
        ref_block_hash = ''

    chain = get_chain(chain_uuid)
    accept_credit_block = chain.accept_credit(
        new_credit.amount,
        ref_block_hash=ref_block_hash
    )
    prev_block_hash = accept_credit_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'AcceptCredit',
        'OnChainID': chain_uuid,
        'Amount': str(new_credit.amount),
        'RefBlockHash': ref_block_hash,
        'BlockHash': accept_credit_block.block_hash,
        'PrevBlockHash': prev_block_hash,
        'Balance': str(accept_credit_block.balance),
        'BalanceDelta': str(accept_credit_block.balance_delta),
        'SerializedBlock': accept_credit_block.serialize()
    })

    return {
        'accept_credit_block_hash': accept_credit_block.block_hash,
    }


class AccessContractOwn(BaseModel):
    other_chain_uuid: UUID
    contract_amount: Decimal
    token: str
    node_uuid: UUID
    frame_uuid: UUID
    expires_in: int
    min_price: Decimal
    details: Optional[dict] = None


@app.post('/chain/{chain_uuid}/block/access_contract_own')
def create_block__access_contract_own(chain_uuid: UUID, access_contract: AccessContractOwn):
    chain_uuid = str(chain_uuid)
    other_chain_uuid = str(access_contract.other_chain_uuid)

    chain = get_chain(chain_uuid)
    access_contract_block = chain.add_access_contract_own(
        other_chain_uuid,
        access_contract.contract_amount,
        access_contract.token,
        str(access_contract.node_uuid),
        str(access_contract.frame_uuid),
        access_contract.expires_in,
        access_contract.min_price,
        details=access_contract.details
    )
    prev_block_hash = access_contract_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'AccessContractOwn',
        'OnChainID': chain_uuid,
        'OtherChainID': other_chain_uuid,
        'ContractAmount': str(access_contract.contract_amount),
        'BlockHash': access_contract_block.block_hash,
        'PrevBlockHash': prev_block_hash,
        'Balance': str(access_contract_block.balance),
        'BalanceDelta': str(access_contract_block.balance_delta),
        'SerializedBlock': access_contract_block.serialize()
    })

    return {
        'access_contract_block_hash': access_contract_block.block_hash,
        'serialized_block': access_contract_block.serialize()
    }


class AccessContractOther(BaseModel):
    other_chain_uuid: UUID
    access_contract_block_hash: str
    contract_amount: Decimal
    token: str
    expires_in: int
    contract_ts: int
    min_price: Decimal
    details: Optional[dict] = None


@app.post('/chain/{chain_uuid}/block/access_contract_other')
def create_block__access_contract_other(chain_uuid: UUID, access_contract: AccessContractOther):
    chain_uuid = str(chain_uuid)
    other_chain_uuid = str(access_contract.other_chain_uuid)

    chain = get_chain(chain_uuid)

    access_contract_block = chain.add_access_contract_other(
        other_chain_uuid,
        access_contract.access_contract_block_hash,
        access_contract.contract_amount,
        access_contract.token,
        access_contract.contract_ts,
        access_contract.expires_in,
        access_contract.min_price,
        details=access_contract.details
    )
    prev_block_hash = access_contract_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'AccessContractOther',
        'OnChainID': chain_uuid,
        'OtherChainID': other_chain_uuid,
        'ContractAmount': str(access_contract.contract_amount),
        'BlockHash': access_contract_block.block_hash,
        'PrevBlockHash': prev_block_hash,
        'Balance': str(access_contract_block.balance),
        'BalanceDelta': str(access_contract_block.balance_delta),
        'SerializedBlock': access_contract_block.serialize()
    })

    return {
        'access_contract_block_hash': access_contract_block.block_hash,
        'serialized_block': access_contract_block.serialize()
    }


class AccessContractOtherEventOpen(BaseModel):
    access_contract_block_hash: str
    other_access_contract_block_hash: str
    amount: Decimal
    details: Optional[dict] = None


@app.post('/chain/{chain_uuid}/block/access_contract_other_event_open')
def create_block__access_contract_other_event_open(chain_uuid: UUID, contract_event: AccessContractOtherEventOpen):
    chain_uuid = str(chain_uuid)
    chain = get_chain(chain_uuid)

    # Verify that the contract block exists
    contract_block = chain.get_block_by_hash(contract_event.other_access_contract_block_hash)
    if not contract_block:
        return {
            'success': False,
            'message': 'Contract not found'
        }

    if contract_block.access_contract_block_hash != contract_event.access_contract_block_hash:
        return {
            'success': False,
            'message': 'Contract ID mismatch'
        }

    access_contract_other_event_open_block = chain.add_access_contract_other_event_open(
        contract_event.access_contract_block_hash,
        contract_event.other_access_contract_block_hash,
        contract_event.amount,
        details=contract_event.details,
    )
    prev_block_hash = access_contract_other_event_open_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'AccessContractOtherEventOpen',
        'OnChainID': chain_uuid,
        'BlockHash': access_contract_other_event_open_block.block_hash,
        'PrevBlockHash': prev_block_hash,
        'Balance': str(access_contract_other_event_open_block.balance),
        'BalanceDelta': str(access_contract_other_event_open_block.balance_delta),
        'SerializedBlock': access_contract_other_event_open_block.serialize()
    })

    return {
        'access_contract_other_event_open_block_hash': access_contract_other_event_open_block.block_hash,
        'serialized_block': access_contract_other_event_open_block.serialize()
    }


class AccessContractOwnEventAsk(BaseModel):
    access_contract_block_hash: str
    other_event_open_block_hash: str
    receive_signal_block_hash: str
    amount: Decimal
    details: Optional[dict] = None


@app.post('/chain/{chain_uuid}/block/access_contract_own_event_ask')
def create_block__access_contract_own_event_ask(chain_uuid: UUID, contract_event: AccessContractOwnEventAsk):
    chain_uuid = str(chain_uuid)
    chain = get_chain(chain_uuid)

    # Verify that the contract block exists
    contract_block = chain.get_block_by_hash(contract_event.access_contract_block_hash)
    if not contract_block:
        return {
            'success': False,
            'message': 'Contract not found: %s %s' % (contract_event.access_contract_block_hash, chain_uuid)
        }

    access_contract_own_event_ask_block = chain.add_access_contract_own_event_ask(
        contract_event.access_contract_block_hash,
        contract_event.other_event_open_block_hash,
        contract_event.receive_signal_block_hash,
        contract_event.amount,
        details=contract_event.details,
    )
    prev_block_hash = access_contract_own_event_ask_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'AccessContractOwnEventAsk',
        'OnChainID': chain_uuid,
        'BlockHash': access_contract_own_event_ask_block.block_hash,
        'PrevBlockHash': prev_block_hash,
        'Balance': str(access_contract_own_event_ask_block.balance),
        'BalanceDelta': str(access_contract_own_event_ask_block.balance_delta),
        'SerializedBlock': access_contract_own_event_ask_block.serialize()
    })

    return {
        'access_contract_other_event_open_block_hash': access_contract_own_event_ask_block.block_hash,
        'serialized_block': access_contract_own_event_ask_block.serialize()
    }


class AccessContractOtherEventClose(BaseModel):
    access_contract_block_hash: str
    access_contract_event_block_hash: str
    other_access_contract_event_block_hash: str
    receive_signal_reward_block_hash: str


@app.post('/chain/{chain_uuid}/block/access_contract_other_event_close')
def create_block__access_contract_other_event_close(chain_uuid: UUID, contract_event: AccessContractOtherEventClose):
    chain_uuid = str(chain_uuid)
    chain = get_chain(chain_uuid)

    # Verify that the contract block exists
    other_contract_block = chain.block_query(
        BlockType.AccessContractOther,
        'access_contract_block_hash',
        contract_event.access_contract_block_hash,
        'str'
    )

    if not other_contract_block:
        return {
            'success': False,
            'message': 'Contract not found'
        }

    other_contract_event_block = chain.get_block_by_hash(contract_event.other_access_contract_event_block_hash)
    if not other_contract_event_block:
        return {
            'success': False,
            'message': 'Contract event not found'
        }

    access_contract_other_event_close_block = chain.add_access_contract_other_event_close(
        contract_event.access_contract_block_hash,
        other_contract_block.block_hash,
        contract_event.access_contract_event_block_hash,
        contract_event.other_access_contract_event_block_hash,
        contract_event.receive_signal_reward_block_hash,
    )
    prev_block_hash = access_contract_other_event_close_block.prev_block_hash

    emit_state_change(service_name, 'BlockAdded', {
        'BlockType': 'AccessContractOtherEventClose',
        'OnChainID': chain_uuid,
        'BlockHash': access_contract_other_event_close_block.block_hash,
        'PrevBlockHash': prev_block_hash,
        'Balance': str(access_contract_other_event_close_block.balance),
        'BalanceDelta': str(access_contract_other_event_close_block.balance_delta),
        'SerializedBlock': access_contract_other_event_close_block.serialize()
    })

    return {
        'access_contract_other_event_close_block_hash': access_contract_other_event_close_block.block_hash,
        'serialized_block': access_contract_other_event_close_block.serialize()
    }


@app.get('/state')
def get_state():
    return get_current_state()


def get_current_state():
    state = {
        'Origin': service_name,
        'Chains': []
    }

    import os
    chain_path = config['DUO_CHAIN_PATH']

    for chain in get_chains(chain_path=chain_path):
        head_block = chain.head_block()
        state['Chains'].append({
            'ID': chain.uuid,
            'BlockType': BlockTypeMap[head_block.block_type],
            'HeadHash': head_block.block_hash,
            'Balance': str(chain.balance()),
            'BlockHeight': head_block.height
        })

    return state
