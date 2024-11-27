from decimal import Decimal
import json


class BlockType:
    Null = 0

    SignalSent = 1
    SignalReceived = 2
    SignalDelivered = 3
    SignalRewardSent = 4
    SignalRewardReceived = 5
    
    Action = 10
    WorkOutput = 11
    
    Debit = 20
    Credit = 21
    CreditAccepted = 22
    CreditRejected = 23

    TargetCreated = 30
    TargetAccepted = 31
    TargetRewardClaimSent = 32
    TargetRewardClaimReceived = 33
    TargetRewardSent = 34
    TargetRewardReceived = 35

    WorkOutputRewardSent = 40
    WorkOutputRewardReceived = 41

    AccessContractOwn = 50
    AccessContractOther = 51
    AccessContractOtherEventOpen = 52
    AccessContractOwnEventAsk = 53
    AccessContractOtherEventClose = 54

    VerificationOpen = 80
    Verification = 81
    VerificationClose = 82

    Reset = 100
    Upgrade = 101


BlockTypeMap = {
    0: 'Null',
    
    1: 'SignalSent',
    2: 'SignalReceived',
    3: 'SignalDelivered',
    4: 'SignalRewardSent',
    5: 'SignalRewardReceived',

    10: 'Action',
    11: 'WorkOutput',

    20: 'Debit',
    21: 'Credit',
    22: 'CreditAccepted',
    23: 'CreditRejected',

    30: 'TargetCreated',
    31: 'TargetAccepted',
    32: 'TargetRewardClaimSent',
    33: 'TargetRewardClaimReceived',
    34: 'TargetRewardSent',
    35: 'TargetRewardReceived',

    40: 'WorkOutputRewardSent',
    41: 'WorkOutputRewardReceived',

    50: 'AccessContractOwn',
    51: 'AccessContractOther',
    52: 'AccessContractOtherEventOpen',
    53: 'AccessContractOwnEventAsk',
    54: 'AccessContractOtherEventClose',

    80: 'VerificationOpen',
    81: 'Verification',
    82: 'VerificationClose',

    100: 'Reset',
    101: 'Upgrade',
}


class BlockHash():
    def __init__(self, hash):
        pass


# Abstract
class Block():
    block_type = None
    dict_props = ()
    
    block_hash = None
    prev_block_hash = BlockHash(None)
    height = 0
    ts = None

    immutable_balance = True
    balance = Decimal('0.0')
    balance_delta = Decimal('0.0')

    def __init__(self, deserialized_block=None):
        import time
        self.ts = int(time.time() * 1000)

        if deserialized_block:
            self.deserialize(deserialized_block)

    def __repr__(self):
        return '<%s Hash=%s, Bal=%s>' % (self.__class__.__name__, self.block_hash, self.balance)

    def generate_hash(self, to_hash=None, assign=True):
        if to_hash is not None:
            assert type(to_hash) in (list, tuple)
        else:
            to_hash = self.get_hashable()

        from hashlib import sha256
        h = sha256()
        for hash_entry in to_hash:
            if type(hash_entry) is not str:
                print(self.block_type, type(hash_entry), hash_entry)

            try:
                assert type(hash_entry) is str
            except AssertionError:
                print('Expected str, got {0}'.format(type(hash_entry)))
                raise
            h.update(hash_entry.encode('utf-8'))

        block_hash = h.hexdigest()
        if assign:
            self.block_hash = block_hash
        return block_hash

    def get_hashable(self):
        return [
            str(self.block_type),
            str(self.prev_block_hash),
            str(self.height),
            str(self.ts),
            str(self.balance),
            str(self.balance_delta),
        ]

    def serialize(self):
        return {
            'block_type': self.block_type,
            'block_hash': self.block_hash,
            'prev_block_hash': self.prev_block_hash,
            'height': self.height,
            'ts': self.ts,
            'balance': str(self.balance),
            'balance_delta': str(self.balance_delta),
        }

    def deserialize(self, serialized_block):
        self.block_hash = serialized_block['block_hash']

        if self.block_type != serialized_block['block_type']:
            raise Exception(f'Expected type {self.block_type}, got type {serialized_block["block_type"]} for block {self.block_hash}')

        self.prev_block_hash = serialized_block['prev_block_hash']
        self.height = int(serialized_block['height'])
        self.ts = int(serialized_block['ts'])
        self.balance = Decimal(serialized_block['balance'])
        self.balance_delta = Decimal(serialized_block['balance_delta'])

    def is_type(self, block_type):
        return self.block_type == block_type

    def validate_hash(self):
        if self.block_hash != self.generate_hash(assign=False):
            raise Exception(f'Hash validation failed for block {self.block_hash}')
        return True

    def update(self, **kwargs):
        self.block_hash = kwargs.get('block_hash', self.block_hash)
        self.prev_block_hash = kwargs.get('prev_block_hash', self.prev_block_hash)
        self.balance = Decimal(kwargs.get('balance', self.balance))
        self.balance_delta = Decimal(kwargs.get('balance_delta', self.balance_delta))


class NullBlock(Block):
    block_type = BlockType.Null


class SignalSent(Block):
    block_type = BlockType.SignalSent
    dict_props = ('signal_data',)
    
    dest_chain_id = None
    signal_data = None
    amount = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.dest_chain_id = kwargs.get('dest_chain_id', self.dest_chain_id)

        amount = kwargs.get('amount')
        if amount is not None:
            self.amount = Decimal(amount)
        
        s = kwargs.get('signal_data', self.signal_data)
        if type(s) is str:
            s = json.loads(s)

        self.signal_data = s

    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'signal_data': self.signal_data,
            'dest_chain_id': self.dest_chain_id,
            'amount': str(self.amount) if self.amount else None
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        signal_data = serialized_block['signal_data']
        if type(signal_data) is dict:
            self.signal_data = signal_data
        else:
            self.signal_data = json.loads(signal_data)

        self.dest_chain_id = serialized_block['dest_chain_id']
        
        amount = serialized_block.get('amount')
        if amount is not None:
            self.amount = Decimal(amount)

    def get_hashable(self):
        hashable = super().get_hashable()

        hashable.append(self.dest_chain_id)
        for key in sorted(self.signal_data.keys()):
            val = self.signal_data[key]

            if type(val) is bool:
                val = str(val)

            hashable.append(key)
            hashable.append(val)

        # FIXME: Backward compat because amount was added after chains existed
        if is_amount(self.amount):
            hashable.append(str(self.amount))

        return hashable

def is_amount(amount):
    if not amount:
        return False

    try:
        x = Decimal(amount)
    except:
        return False
    else:
        return bool(x)


class SignalReceived(Block):
    block_type = BlockType.SignalReceived
    dict_props = ('signal_data',)
    
    src_chain_id = None
    send_signal_block_hash = None
    signal_data = None
    amount = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.src_chain_id = kwargs.get('src_chain_id', self.src_chain_id)
        self.send_signal_block_hash = kwargs.get('send_signal_block_hash', self.send_signal_block_hash)

        amount = kwargs.get('amount')
        if amount is not None:
            self.amount = Decimal(amount)

        s = kwargs.get('signal_data', self.signal_data)
        if type(s) is str:
            s = json.loads(s)

        self.signal_data = s

    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'signal_data': json.dumps(self.signal_data),
            'send_signal_block_hash': self.send_signal_block_hash,
            'src_chain_id': self.src_chain_id,
            'amount': str(self.amount) if self.amount else None
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        signal_data = serialized_block['signal_data']
        if type(signal_data) is dict:
            self.signal_data = signal_data
        else:
            self.signal_data = json.loads(signal_data)

        self.src_chain_id = serialized_block['src_chain_id']
        self.send_signal_block_hash = serialized_block['send_signal_block_hash']

        amount = serialized_block.get('amount')
        if amount is not None:
            self.amount = Decimal(amount)

    def get_hashable(self):
        hashable = super().get_hashable()

        hashable.append(self.src_chain_id)
        hashable.append(self.send_signal_block_hash)
        for key in sorted(self.signal_data.keys()):
            val = self.signal_data[key]

            if type(val) is bool:
                val = str(val)

            hashable.append(key)
            hashable.append(val)

        # FIXME: Backward compat because amount was added after chains existed
        if is_amount(self.amount):
            hashable.append(str(self.amount))

        return hashable


class SignalDelivered(Block):
    block_type = BlockType.SignalDelivered
    
    src_chain_id = None
    receive_signal_block_hash = None
    cost = 1
    amount = None
    activity_id = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.activity_id = kwargs.get('activity_id', self.activity_id)
        self.src_chain_id = kwargs.get('src_chain_id', self.src_chain_id)
        self.receive_signal_block_hash = kwargs.get('receive_signal_block_hash', self.receive_signal_block_hash)
        self.cost = int(kwargs.get('cost', self.cost))

        amount = kwargs.get('amount')
        if amount is not None:
            self.amount = Decimal(amount)

    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'activity_id': self.activity_id,
            'receive_signal_block_hash': self.receive_signal_block_hash,
            'src_chain_id': self.src_chain_id,
            'cost': self.cost,
            'amount': str(self.amount) if self.amount else None
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.activity_id = serialized_block['activity_id']
        self.src_chain_id = serialized_block['src_chain_id']
        self.receive_signal_block_hash = serialized_block['receive_signal_block_hash']
        self.cost = int(serialized_block['cost'])

        amount = serialized_block.get('amount')
        if amount is not None:
            self.amount = Decimal(amount)

    def get_hashable(self):
        hashable = super().get_hashable()

        hashable.append(self.activity_id)
        hashable.append(self.src_chain_id)
        hashable.append(self.receive_signal_block_hash)
        hashable.append(str(self.cost))
        hashable.append(str(self.amount))

        return hashable


class SignalRewardSent(Block):
    block_type = BlockType.SignalRewardSent
    immutable_balance = False

    dest_chain_id = None
    action_block_hash = None
    deliver_signal_block_hash = None
    amount = None
    accepted_amount = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.dest_chain_id = kwargs.get('dest_chain_id', self.dest_chain_id)
        self.action_block_hash = kwargs.get('action_block_hash', self.action_block_hash)
        self.deliver_signal_block_hash = kwargs.get('deliver_signal_block_hash', self.deliver_signal_block_hash)
        self.amount = Decimal(kwargs.get('amount', self.amount))

        accepted_amount = kwargs.get('accepted_amount')
        if accepted_amount is not None:
            self.accepted_amount = Decimal(accepted_amount)

    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'dest_chain_id': self.dest_chain_id,
            'deliver_signal_block_hash': self.deliver_signal_block_hash,
            'action_block_hash': self.action_block_hash,
            'amount': str(self.amount),
            'accepted_amount': str(self.accepted_amount) if self.accepted_amount else None,
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.dest_chain_id = serialized_block['dest_chain_id']

        # This field may not be present since it was added after chains existed
        self.action_block_hash = serialized_block.get('action_block_hash')

        self.deliver_signal_block_hash = serialized_block['deliver_signal_block_hash']
        self.amount = Decimal(serialized_block['amount'])
        self.accepted_amount = serialized_block.get('accepted_amount', '')

    def get_hashable(self):
        hashable = super().get_hashable()

        hashable.append(self.dest_chain_id)
        hashable.append(str(self.action_block_hash))
        hashable.append(self.deliver_signal_block_hash)
        hashable.append(str(self.amount))
        hashable.append(str(self.accepted_amount))

        return hashable


class SignalRewardReceived(Block):
    block_type = BlockType.SignalRewardReceived
    immutable_balance = False

    src_chain_id = None
    send_signal_reward_block_hash = None
    amount = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.src_chain_id = kwargs.get('src_chain_id', self.src_chain_id)
        self.send_signal_reward_block_hash = kwargs.get('send_signal_reward_block_hash', self.send_signal_reward_block_hash)
        self.amount = Decimal(kwargs.get('amount', self.amount))

    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'src_chain_id': self.src_chain_id,
            'send_signal_reward_block_hash': self.send_signal_reward_block_hash,
            'amount': str(self.amount),
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.src_chain_id = serialized_block['src_chain_id']
        self.send_signal_reward_block_hash = serialized_block['send_signal_reward_block_hash']
        self.amount = Decimal(serialized_block['amount'])

    def get_hashable(self):
        hashable = super().get_hashable()

        hashable.append(self.src_chain_id)
        hashable.append(self.send_signal_reward_block_hash)
        hashable.append(str(self.amount))

        return hashable


class Verification(Block):
    block_type = BlockType.Verification

    src_chain_id = None
    prev_verification_block_hash = None
    other_verification_block_hash = None
    chain_length = None
    sub_chain_balance = None
    sub_chain_length = None
    sub_chain_hash = None
    full_verification = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.src_chain_id = kwargs.get('src_chain_id', self.src_chain_id)
        self.prev_verification_block_hash = kwargs.get('prev_verification_block_hash', self.prev_verification_block_hash)
        self.other_verification_block_hash = kwargs.get('other_verification_block_hash', self.other_verification_block_hash)
        self.chain_length = int(kwargs.get('chain_length', self.chain_length))
        self.sub_chain_balance = Decimal(kwargs.get('sub_chain_balance', self.sub_chain_balance))
        self.sub_chain_length = int(kwargs.get('sub_chain_length', self.sub_chain_length))
        self.sub_chain_hash = kwargs.get('sub_chain_hash', self.sub_chain_hash)
        self.full_verification = bool(kwargs.get('full_verification', self.full_verification))

    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'src_chain_id': self.src_chain_id,
            'prev_verification_block_hash': self.prev_verification_block_hash,
            'other_verification_block_hash': self.other_verification_block_hash,
            'chain_length': str(self.chain_length),
            'sub_chain_balance': str(self.sub_chain_balance),
            'sub_chain_length': str(self.sub_chain_length),
            'sub_chain_hash': self.sub_chain_hash,
            'full_verification': self.full_verification
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.src_chain_id = serialized_block['src_chain_id']
        self.prev_verification_block_hash = serialized_block['prev_verification_block_hash']
        self.other_verification_block_hash = serialized_block['other_verification_block_hash']
        self.chain_length = int(serialized_block['chain_length'])
        self.sub_chain_balance = Decimal(serialized_block['sub_chain_balance'])
        self.sub_chain_length = int(serialized_block['sub_chain_length'])
        self.sub_chain_hash = serialized_block['sub_chain_hash']
        self.full_verification = bool(serialized_block['full_verification'])

    def get_hashable(self):
        hashable = super().get_hashable()

        hashable.append(self.src_chain_id)
        hashable.append(str(self.prev_verification_block_hash))
        hashable.append(str(self.other_verification_block_hash))
        hashable.append(str(self.chain_length))
        hashable.append(str(self.sub_chain_balance))
        hashable.append(str(self.sub_chain_length))
        hashable.append(self.sub_chain_hash)
        hashable.append(str(self.full_verification))

        return hashable


class VerificationOpen(Block):
    block_type = BlockType.VerificationOpen

    dest_chain_id = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.dest_chain_id = kwargs.get('dest_chain_id', self.dest_chain_id)

    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'dest_chain_id': self.dest_chain_id,
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.dest_chain_id = serialized_block['dest_chain_id']

    def get_hashable(self):
        hashable = super().get_hashable()

        hashable.append(self.dest_chain_id)

        return hashable


class VerificationClose(Block):
    block_type = BlockType.VerificationClose

    dest_chain_id = None
    open_verification_block_hash = None
    other_verification_block_hash = None
    chain_length = None
    sub_chain_balance = None
    sub_chain_length = None
    sub_chain_hash = None
    full_verification = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.dest_chain_id = kwargs.get('dest_chain_id', self.dest_chain_id)
        self.open_verification_block_hash = kwargs.get('open_verification_block_hash', self.open_verification_block_hash)
        self.other_verification_block_hash = kwargs.get('other_verification_block_hash', self.other_verification_block_hash)
        self.chain_length = int(kwargs.get('chain_length', self.chain_length))
        self.sub_chain_balance = Decimal(kwargs.get('sub_chain_balance', self.sub_chain_balance))
        self.sub_chain_length = int(kwargs.get('sub_chain_length', self.sub_chain_length))
        self.sub_chain_hash = kwargs.get('sub_chain_hash', self.sub_chain_hash)
        self.full_verification = bool(kwargs.get('full_verification', self.full_verification))

    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'dest_chain_id': self.dest_chain_id,
            'open_verification_block_hash': self.open_verification_block_hash,
            'other_verification_block_hash': self.other_verification_block_hash,
            'chain_length': str(self.chain_length),
            'sub_chain_balance': str(self.sub_chain_balance),
            'sub_chain_length': str(self.sub_chain_length),
            'sub_chain_hash': self.sub_chain_hash,
            'full_verification': self.full_verification
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.dest_chain_id = serialized_block['dest_chain_id']
        self.open_verification_block_hash = serialized_block['open_verification_block_hash']
        self.other_verification_block_hash = serialized_block['other_verification_block_hash']
        self.chain_length = int(serialized_block['chain_length'])
        self.sub_chain_balance = Decimal(serialized_block['sub_chain_balance'])
        self.sub_chain_length = int(serialized_block['sub_chain_length'])
        self.sub_chain_hash = serialized_block['sub_chain_hash']
        self.full_verification = bool(serialized_block['full_verification'])

    def get_hashable(self):
        hashable = super().get_hashable()

        hashable.append(self.dest_chain_id)
        hashable.append(str(self.open_verification_block_hash))
        hashable.append(str(self.other_verification_block_hash))
        hashable.append(str(self.chain_length))
        hashable.append(str(self.sub_chain_balance))
        hashable.append(str(self.sub_chain_length))
        hashable.append(self.sub_chain_hash)
        hashable.append(str(self.full_verification))

        return hashable


class BaseAction(Block):
    block_type = None
    dict_props = ('signal_data',)

    action_id = None
    activity_id = None
    refs = None
    action_ts = None

    def __init__(self, deserialized_block=None):
        import time
        self.action_ts = int(time.time() * 1000)
        self.refs = {}
        
        super().__init__(deserialized_block=deserialized_block)
    
    def update(self, **kwargs):
        super().update(**kwargs)

        self.action_id = kwargs.get('action_id', self.action_id)
        self.activity_id = kwargs.get('activity_id', self.activity_id)

        # FIXME: refs is a struct. Probably don't want to always autoreplace it
        r = kwargs.get('refs', self.refs)
        if type(r) is str:
            r = json.loads(r)
        self.refs = r

        self.action_ts = int(kwargs.get('action_ts', self.action_ts))

    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'action_id': self.action_id,
            'activity_id': self.activity_id,
            'action_ts': str(self.action_ts),
            'refs': self.refs,
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.action_id = serialized_block['action_id']
        self.activity_id = serialized_block['activity_id']
        self.action_ts = int(serialized_block['action_ts'])
        self.refs = serialized_block.get('refs', {})

    def get_hashable(self):
        hashable = super().get_hashable()

        hashable.append(self.action_id)
        hashable.append(self.activity_id)
        hashable.append(str(self.action_ts))

        for key in sorted(self.refs.keys()):
            hashable.append('.'.join(sorted(self.refs[key])))

        return hashable


class Action(BaseAction):
    block_type = BlockType.Action

    deliver_signal_block_hash = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.deliver_signal_block_hash = kwargs.get('deliver_signal_block_hash', self.deliver_signal_block_hash)

    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'deliver_signal_block_hash': self.deliver_signal_block_hash,
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.deliver_signal_block_hash = serialized_block['deliver_signal_block_hash']

    def get_hashable(self):
        hashable = super().get_hashable()
        hashable.append(str(self.deliver_signal_block_hash))

        return hashable


class WorkOutput(BaseAction):
    block_type = BlockType.WorkOutput

    details = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.details = kwargs.get('details', self.details)

    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'details': self.details,
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.details = serialized_block['details']

    def get_hashable(self):
        hashable = super().get_hashable()

        # FIXME: Decide on details schema
        # hashable.append(str(self.details))

        return hashable


class TargetCreated(Block):
    block_type = BlockType.TargetCreated

    name = None
    target_id = None
    reward_per = None
    reward_pool = None
    priors = None
    conditions = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.name = kwargs.get('name', self.name)
        self.target_id = kwargs.get('target_id', self.target_id)
        self.reward_per = Decimal(kwargs.get('reward_per', self.reward_per))
        self.reward_pool = Decimal(kwargs.get('reward_pool', self.reward_pool))
        self.priors = kwargs.get('priors', self.priors)
        self.conditions = kwargs.get('conditions', self.conditions)
        
    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'name': self.name,
            'target_id': self.target_id,
            'reward_per': str(self.reward_per),
            'reward_pool': str(self.reward_pool),
            'priors': self.priors,
            'conditions': self.conditions,
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.name = serialized_block['name']
        self.target_id = serialized_block['target_id']
        self.reward_per = Decimal(serialized_block['reward_per'])
        self.reward_pool = Decimal(serialized_block['reward_pool'])
        self.priors = serialized_block['priors']
        self.conditions = serialized_block['conditions']

    def get_hashable(self):
        hashable = super().get_hashable()

        hashable.append(self.name)
        hashable.append(self.target_id)
        hashable.append(str(self.reward_per))
        hashable.append(str(self.reward_pool))

        # FIXME: Decide on priors schema
        # hashable.append(str(self.priors))

        # FIXME: Decide on conditions schema
        # hashable.append(str(self.conditions))

        return hashable


class TargetAccepted(Block):
    block_type = BlockType.TargetAccepted

    src_chain_id = None
    #action_block_hash = None
    target_id = None
    target_block_hash = None
    target_details = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.src_chain_id = kwargs.get('src_chain_id', self.src_chain_id)
        #self.action_block_hash = kwargs.get('action_block_hash', self.action_block_hash)
        self.target_id = kwargs.get('target_id', self.target_id)
        self.target_block_hash = kwargs.get('target_block_hash', self.target_block_hash)
        self.target_details = kwargs.get('target_details', self.target_details)
        
    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'src_chain_id': self.src_chain_id,
            #'action_block_hash': self.action_block_hash,
            'target_id': self.target_id,
            'target_block_hash': self.target_block_hash,
            'target_details': self.target_details,
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.src_chain_id = serialized_block['src_chain_id']
        #self.action_block_hash = serialized_block['action_block_hash']
        self.target_id = serialized_block['target_id']
        self.target_block_hash = serialized_block['target_block_hash']
        self.target_details = serialized_block['target_details']

    def get_hashable(self):
        hashable = super().get_hashable()
        hashable.append(self.src_chain_id)
        #hashable.append(self.action_block_hash)
        hashable.append(self.target_id)
        hashable.append(self.target_block_hash)

        # FIXME: Decide on target_details schema
        # hashable.append(str(self.target_details))

        return hashable


class TargetRewardClaimSent(Block):
    block_type = BlockType.TargetRewardClaimSent

    dest_chain_id = None
    target_block_hash = None
    work_output_block_hash = None
    work_output_details = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.dest_chain_id = kwargs.get('dest_chain_id', self.dest_chain_id)
        self.target_block_hash = kwargs.get('target_block_hash', self.target_block_hash)
        self.work_output_block_hash = kwargs.get('work_output_block_hash', self.work_output_block_hash)
        self.work_output_details = kwargs.get('work_output_details', self.work_output_details)
        
    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'dest_chain_id': self.dest_chain_id,
            'target_block_hash': self.target_block_hash,
            'work_output_block_hash': self.work_output_block_hash,
            'work_output_details': self.work_output_details,
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.dest_chain_id = serialized_block['dest_chain_id']
        self.target_block_hash = serialized_block['target_block_hash']
        self.work_output_block_hash = serialized_block['work_output_block_hash']
        self.work_output_details = serialized_block['work_output_details']

    def get_hashable(self):
        hashable = super().get_hashable()
        hashable.append(self.dest_chain_id)
        hashable.append(self.target_block_hash)
        hashable.append(self.work_output_block_hash)

        # FIXME: Decide on work_output_details schema
        # hashable.append(str(self.work_output_details))

        return hashable


class TargetRewardClaimReceived(Block):
    block_type = BlockType.TargetRewardClaimReceived

    src_chain_id = None
    target_block_hash = None
    send_target_reward_claim_block_hash = None
    work_output_block_hash = None
    work_output_details = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.src_chain_id = kwargs.get('src_chain_id', self.src_chain_id)
        self.target_block_hash = kwargs.get('target_block_hash', self.target_block_hash)
        self.send_target_reward_claim_block_hash = kwargs.get('send_target_reward_claim_block_hash', self.send_target_reward_claim_block_hash)
        self.work_output_block_hash = kwargs.get('work_output_block_hash', self.work_output_block_hash)
        self.work_output_details = kwargs.get('work_output_details', self.work_output_details)
        
    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'src_chain_id': self.src_chain_id,
            'target_block_hash': self.target_block_hash,
            'send_target_reward_claim_block_hash': self.send_target_reward_claim_block_hash,
            'work_output_block_hash': self.work_output_block_hash,
            'work_output_details': self.work_output_details,
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.src_chain_id = serialized_block['src_chain_id']
        self.target_block_hash = serialized_block['target_block_hash']
        self.send_target_reward_claim_block_hash = serialized_block['send_target_reward_claim_block_hash']
        self.work_output_block_hash = serialized_block['work_output_block_hash']
        self.work_output_details = serialized_block['work_output_details']

    def get_hashable(self):
        hashable = super().get_hashable()
        hashable.append(self.src_chain_id)
        hashable.append(self.target_block_hash)
        hashable.append(self.send_target_reward_claim_block_hash)
        hashable.append(self.work_output_block_hash)

        # FIXME: Decide on work_output_details schema
        # hashable.append(str(self.work_output_details))

        return hashable


class TargetRewardSent(Block):
    block_type = BlockType.TargetRewardSent

    dest_chain_id = None
    target_block_hash = None
    receive_target_reward_claim_block_hash = None
    amount = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.dest_chain_id = kwargs.get('dest_chain_id', self.dest_chain_id)
        self.target_block_hash = kwargs.get('target_block_hash', self.target_block_hash)
        self.receive_target_reward_claim_block_hash = kwargs.get('receive_target_reward_claim_block_hash', self.receive_target_reward_claim_block_hash)
        self.amount = Decimal(kwargs.get('amount', self.amount))
        
    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'dest_chain_id': self.dest_chain_id,
            'target_block_hash': self.target_block_hash,
            'receive_target_reward_claim_block_hash': self.receive_target_reward_claim_block_hash,
            'amount': str(self.amount),
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.dest_chain_id = serialized_block['dest_chain_id']
        self.target_block_hash = serialized_block['target_block_hash']
        self.receive_target_reward_claim_block_hash = serialized_block['receive_target_reward_claim_block_hash']
        self.amount = Decimal(serialized_block['amount'])

    def get_hashable(self):
        hashable = super().get_hashable()

        hashable.append(self.dest_chain_id)
        hashable.append(self.target_block_hash)
        hashable.append(self.receive_target_reward_claim_block_hash)
        hashable.append(str(self.amount))

        return hashable


class TargetRewardReceived(Block):
    block_type = BlockType.TargetRewardReceived

    src_chain_id = None
    target_block_hash = None
    send_target_reward_block_hash = None
    amount = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.src_chain_id = kwargs.get('src_chain_id', self.src_chain_id)
        self.target_block_hash = kwargs.get('target_block_hash', self.target_block_hash)
        self.send_target_reward_block_hash = kwargs.get('send_target_reward_block_hash', self.send_target_reward_block_hash)
        self.amount = Decimal(kwargs.get('amount', self.amount))
        
    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'src_chain_id': self.src_chain_id,
            'target_block_hash': self.target_block_hash,
            'send_target_reward_block_hash': self.send_target_reward_block_hash,
            'amount': str(self.amount),
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.src_chain_id = serialized_block['src_chain_id']
        self.target_block_hash = serialized_block['target_block_hash']
        self.send_target_reward_block_hash = serialized_block['send_target_reward_block_hash']
        self.amount = Decimal(serialized_block['amount'])

    def get_hashable(self):
        hashable = super().get_hashable()

        hashable.append(self.src_chain_id)
        hashable.append(self.target_block_hash)
        hashable.append(self.send_target_reward_block_hash)
        hashable.append(str(self.amount))

        return hashable


class Debit(Block):
    block_type = BlockType.Debit
    immutable_balance = False

    ref_block_hash = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.ref_block_hash = kwargs.get('ref_block_hash', self.ref_block_hash)
        self.balance_delta = Decimal(kwargs.get('balance_delta', self.balance_delta))

    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'ref_block_hash': self.ref_block_hash,
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.ref_block_hash = serialized_block['ref_block_hash']

    def get_hashable(self):
        hashable = super().get_hashable()
        hashable.append(self.ref_block_hash)

        return hashable


class CreditAccepted(Block):
    block_type = BlockType.CreditAccepted

    ref_block_hash = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.ref_block_hash = kwargs.get('ref_block_hash', self.ref_block_hash)
        self.balance_delta = Decimal(kwargs.get('balance_delta', self.balance_delta))
        
    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'ref_block_hash': self.ref_block_hash,
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.ref_block_hash = serialized_block['ref_block_hash']

    def get_hashable(self):
        hashable = super().get_hashable()
        hashable.append(self.ref_block_hash)

        return hashable


class CreditRejected(Block):
    block_type = BlockType.CreditRejected

    amount = None
    ref_block_hash = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.ref_block_hash = kwargs.get('ref_block_hash', self.ref_block_hash)
        self.amount = Decimal(kwargs.get('amount', self.amount))
        
    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'ref_block_hash': self.ref_block_hash,
            'amount': str(self.amount),
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.ref_block_hash = serialized_block['ref_block_hash']
        self.amount = Decimal(serialized_block['amount'])

    def get_hashable(self):
        hashable = super().get_hashable()
        hashable.append(self.ref_block_hash)
        hashable.append(str(self.amount))

        return hashable


class AccessContractOwn(Block):
    block_type = BlockType.AccessContractOwn

    dest_chain_id = None
    contract_amount = None
    token = None
    node_uuid = None
    frame_uuid = None
    expires_in = None
    min_price = None
    details = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.dest_chain_id = kwargs.get('dest_chain_id', self.dest_chain_id)
        self.contract_amount = Decimal(kwargs.get('contract_amount', self.contract_amount))
        self.token = kwargs.get('token', self.token)
        self.node_uuid = kwargs.get('node_uuid', self.node_uuid)
        self.frame_uuid = kwargs.get('frame_uuid', self.frame_uuid)
        self.expires_in = int(kwargs.get('expires_in', self.expires_in))
        self.min_price = Decimal(kwargs.get('min_price', self.min_price))
        self.details = kwargs.get('details', self.details)

    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'dest_chain_id': self.dest_chain_id,
            'contract_amount': str(self.contract_amount),
            'token': self.token,
            'node_uuid': self.node_uuid,
            'frame_uuid': self.frame_uuid,
            'expires_in': self.expires_in,
            'min_price': str(self.min_price),
            'details': self.details,
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.dest_chain_id = serialized_block['dest_chain_id']
        self.contract_amount = Decimal(serialized_block['contract_amount'])
        self.token = serialized_block['token']
        self.node_uuid = serialized_block['node_uuid']
        self.frame_uuid = serialized_block['frame_uuid']
        self.expires_in = int(serialized_block['expires_in'])
        self.min_price = Decimal(serialized_block['min_price'])
        self.details = serialized_block['details']

    def get_hashable(self):
        hashable = super().get_hashable()

        hashable.append(self.dest_chain_id)
        hashable.append(str(self.contract_amount))
        hashable.append(self.token)
        hashable.append(self.node_uuid)
        hashable.append(self.frame_uuid)
        hashable.append(str(self.expires_in))
        hashable.append(str(self.min_price))

        # FIXME: Decide on details schema
        # hashable.append(str(self.details))

        return hashable


class AccessContractOther(Block):
    block_type = BlockType.AccessContractOther

    src_chain_id = None
    access_contract_block_hash = None
    contract_amount = None
    token = None
    contract_ts = None
    expires_in = None
    min_price = None
    details = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.src_chain_id = kwargs.get('src_chain_id', self.src_chain_id)
        self.access_contract_block_hash = kwargs.get('access_contract_block_hash', self.access_contract_block_hash)
        self.contract_amount = Decimal(kwargs.get('contract_amount', self.contract_amount))
        self.token = kwargs.get('token', self.token)
        self.expires_in = int(kwargs.get('expires_in', self.expires_in))
        self.contract_ts = int(kwargs.get('contract_ts', self.contract_ts))
        self.min_price = Decimal(kwargs.get('min_price', self.min_price))
        self.details = kwargs.get('details', self.details)

    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'src_chain_id': self.src_chain_id,
            'access_contract_block_hash': self.access_contract_block_hash,
            'contract_amount': str(self.contract_amount),
            'token': self.token,
            'expires_in': self.expires_in,
            'contract_ts': self.contract_ts,
            'min_price': str(self.min_price),
            'details': self.details,
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.src_chain_id = serialized_block['src_chain_id']
        self.access_contract_block_hash = serialized_block['access_contract_block_hash']
        self.contract_amount = Decimal(serialized_block['contract_amount'])
        self.token = serialized_block['token']
        self.expires_in = int(serialized_block['expires_in'])
        self.contract_ts = int(serialized_block['contract_ts'])
        self.min_price = Decimal(serialized_block['min_price'])
        self.details = serialized_block['details']

    def get_hashable(self):
        hashable = super().get_hashable()

        hashable.append(self.src_chain_id)
        hashable.append(self.access_contract_block_hash)
        hashable.append(str(self.contract_amount))
        hashable.append(self.token)
        hashable.append(str(self.expires_in))
        hashable.append(str(self.contract_ts))
        hashable.append(str(self.min_price))

        # FIXME: Decide on details schema
        # hashable.append(str(self.details))

        return hashable


class AccessContractOtherEventOpen(Block):
    block_type = BlockType.AccessContractOtherEventOpen

    access_contract_block_hash = None
    other_access_contract_block_hash = None
    amount = None
    details = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.access_contract_block_hash = kwargs.get('access_contract_block_hash', self.access_contract_block_hash)
        self.other_access_contract_block_hash = kwargs.get('other_access_contract_block_hash', self.other_access_contract_block_hash)
        self.amount = Decimal(kwargs.get('amount', self.amount))
        self.details = kwargs.get('details', self.details)

    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'access_contract_block_hash': self.access_contract_block_hash,
            'other_access_contract_block_hash': self.other_access_contract_block_hash,
            'amount': str(self.amount),
            'details': self.details,
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.access_contract_block_hash = serialized_block['access_contract_block_hash']
        self.other_access_contract_block_hash = serialized_block['other_access_contract_block_hash']
        self.amount = Decimal(serialized_block['amount'])
        self.details = serialized_block['details']

    def get_hashable(self):
        hashable = super().get_hashable()

        hashable.append(self.access_contract_block_hash)
        hashable.append(self.other_access_contract_block_hash)
        hashable.append(str(self.amount))

        # FIXME: Decide on details schema
        # hashable.append(str(self.details))

        return hashable


class AccessContractOwnEventAsk(Block):
    block_type = BlockType.AccessContractOwnEventAsk

    access_contract_block_hash = None
    other_event_open_block_hash = None
    receive_signal_block_hash = None
    amount = None
    details = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.access_contract_block_hash = kwargs.get('access_contract_block_hash', self.access_contract_block_hash)
        self.other_event_open_block_hash = kwargs.get('other_event_open_block_hash', self.other_event_open_block_hash)
        self.receive_signal_block_hash = kwargs.get('receive_signal_block_hash', self.receive_signal_block_hash)
        self.amount = Decimal(kwargs.get('amount', self.amount))
        self.details = kwargs.get('details', self.details)

    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'access_contract_block_hash': self.access_contract_block_hash,
            'other_event_open_block_hash': self.other_event_open_block_hash,
            'receive_signal_block_hash': self.receive_signal_block_hash,
            'amount': str(self.amount),
            'details': self.details,
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.access_contract_block_hash = serialized_block['access_contract_block_hash']
        self.other_event_open_block_hash = serialized_block['other_event_open_block_hash']
        self.receive_signal_block_hash = serialized_block['receive_signal_block_hash']
        self.amount = Decimal(serialized_block['amount'])
        self.details = serialized_block['details']

    def get_hashable(self):
        hashable = super().get_hashable()

        hashable.append(self.access_contract_block_hash)
        hashable.append(self.other_event_open_block_hash)
        hashable.append(self.receive_signal_block_hash)
        hashable.append(str(self.amount))

        # FIXME: Decide on details schema
        # hashable.append(str(self.details))

        return hashable


class AccessContractOtherEventClose(Block):
    block_type = BlockType.AccessContractOtherEventClose

    access_contract_block_hash = None
    other_access_contract_block_hash = None
    access_contract_event_block_hash = None
    other_access_contract_event_block_hash = None
    receive_signal_reward_block_hash = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.access_contract_block_hash = kwargs.get('access_contract_block_hash', self.access_contract_block_hash)
        self.other_access_contract_block_hash = kwargs.get('other_access_contract_block_hash', self.other_access_contract_block_hash)
        self.access_contract_event_block_hash = kwargs.get('access_contract_event_block_hash', self.access_contract_event_block_hash)
        self.other_access_contract_event_block_hash = kwargs.get('other_access_contract_event_block_hash', self.other_access_contract_event_block_hash)
        self.receive_signal_reward_block_hash = kwargs.get('receive_signal_reward_block_hash', self.receive_signal_reward_block_hash)
        
    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'access_contract_block_hash': self.access_contract_block_hash,
            'other_access_contract_block_hash': self.other_access_contract_block_hash,
            'access_contract_event_block_hash': self.access_contract_event_block_hash,
            'other_access_contract_event_block_hash': self.other_access_contract_event_block_hash,
            'receive_signal_reward_block_hash': self.receive_signal_reward_block_hash,
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.access_contract_block_hash = serialized_block['access_contract_block_hash']
        self.other_access_contract_block_hash = serialized_block['other_access_contract_block_hash']
        self.access_contract_event_block_hash = serialized_block['access_contract_event_block_hash']
        self.other_access_contract_event_block_hash = serialized_block['other_access_contract_event_block_hash']
        self.receive_signal_reward_block_hash = serialized_block['receive_signal_reward_block_hash']

    def get_hashable(self):
        hashable = super().get_hashable()

        hashable.append(self.access_contract_block_hash)
        hashable.append(self.other_access_contract_block_hash)
        hashable.append(self.access_contract_event_block_hash)
        hashable.append(self.other_access_contract_event_block_hash)
        hashable.append(self.receive_signal_reward_block_hash)

        return hashable


class WorkOutputRewardSent(Block):
    block_type = BlockType.WorkOutputRewardSent

    dest_chain_id = None
    amount = None
    work_output_block_hash = None
    details = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.dest_chain_id = kwargs.get('dest_chain_id', self.dest_chain_id)
        self.amount = Decimal(kwargs.get('amount', self.amount))
        self.work_output_block_hash = kwargs.get('work_output_block_hash', self.work_output_block_hash)
        self.details = kwargs.get('details', self.details)
        
    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'dest_chain_id': self.dest_chain_id,
            'amount': str(self.amount),
            'work_output_block_hash': self.work_output_block_hash,
            'details': self.details,
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.dest_chain_id = serialized_block['dest_chain_id']
        self.amount = Decimal(serialized_block['amount'])
        self.work_output_block_hash = serialized_block['work_output_block_hash']
        self.details = serialized_block['details']

    def get_hashable(self):
        hashable = super().get_hashable()

        hashable.append(self.dest_chain_id)
        hashable.append(str(self.amount))
        hashable.append(self.work_output_block_hash)

        # FIXME: Decide on details schema
        # hashable.append(str(self.details))

        return hashable


class WorkOutputRewardReceived(Block):
    block_type = BlockType.WorkOutputRewardReceived

    src_chain_id = None
    amount = None
    work_output_block_hash = None
    send_work_output_reward_block_hash = None
    details = None

    def update(self, **kwargs):
        super().update(**kwargs)

        self.src_chain_id = kwargs.get('src_chain_id', self.src_chain_id)
        self.amount = Decimal(kwargs.get('amount', self.amount))
        self.work_output_block_hash = kwargs.get('work_output_block_hash', self.work_output_block_hash)
        self.send_work_output_reward_block_hash = kwargs.get('send_work_output_reward_block_hash', self.send_work_output_reward_block_hash)
        self.details = kwargs.get('details', self.details)
        
    def serialize(self):
        serialized = super().serialize()
        serialized.update({
            'src_chain_id': self.src_chain_id,
            'amount': str(self.amount),
            'work_output_block_hash': self.work_output_block_hash,
            'send_work_output_reward_block_hash': self.send_work_output_reward_block_hash,
            'details': self.details,
        })

        return serialized

    def deserialize(self, serialized_block):
        super().deserialize(serialized_block)

        self.src_chain_id = serialized_block['src_chain_id']
        self.amount = Decimal(serialized_block['amount'])
        self.work_output_block_hash = serialized_block['work_output_block_hash']
        self.send_work_output_reward_block_hash = serialized_block['send_work_output_reward_block_hash']
        self.details = serialized_block['details']

    def get_hashable(self):
        hashable = super().get_hashable()

        hashable.append(self.src_chain_id)
        hashable.append(str(self.amount))
        hashable.append(self.work_output_block_hash)
        hashable.append(self.send_work_output_reward_block_hash)

        # FIXME: Decide on details schema
        # hashable.append(str(self.details))

        return hashable


class Reset(Block):
    block_type = BlockType.Reset


class Upgrade(Block):
    block_type = BlockType.Upgrade

