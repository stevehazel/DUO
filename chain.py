#!/usr/bin/python3

import time
from glom import glom

from decimal import Decimal
from collections import defaultdict

from blocks import BlockType, NullBlock, \
    SignalSent, SignalReceived, SignalDelivered, \
    SignalRewardSent, SignalRewardReceived, \
    VerificationOpen, Verification, VerificationClose, \
    Action, WorkOutput, Debit, \
    TargetCreated, TargetAccepted, \
    TargetRewardClaimSent, TargetRewardClaimReceived, \
    TargetRewardSent, TargetRewardReceived, \
    Debit, CreditAccepted, CreditRejected, \
    AccessContractOwn, AccessContractOther, \
    AccessContractOwnEventAsk, AccessContractOtherEventOpen, AccessContractOtherEventClose, \
    WorkOutputRewardSent, WorkOutputRewardReceived, \
    Reset, Upgrade


from blocks import BlockTypeMap

class ChainSeed():
    val = None
    def __init__(self, val):
        self.val = val

    def __repr__(self):
        return str(self.val)


class ChainID():
    val = None
    def __init__(self, val):
        self.val = val

    def __repr__(self):
        return str(self.val)


class SignalID():
    val = None
    def __init__(self, val):
        self.val = val


class ChainInterface():
    def __init__(self, chains=None):
        if chains:
            self.chains = chains
        else:
            self.chains = {}

    def get_chain(self, chain_id):
        return self.chains.get(str(chain_id))

    def add_chain(self, chain):
        self.chains[chain.uuid] = chain

    def send_signal(self, src_chain, dest_chain_id, send_signal_block_hash, signal_data, amount=None):
        dest_chain = self.get_chain(dest_chain_id)

        if not dest_chain:
            print(f'dest chain not known: {dest_chain_id}')
            return

        self.receive_signal(src_chain, dest_chain, send_signal_block_hash, signal_data, amount)

    def receive_signal(self, src_chain, dest_chain, send_signal_block_hash, signal_data, amount=None):
        if not amount or amount < 1 or type(amount) is not Decimal:
            amount = Decimal('1.00')

        receive_signal_block = dest_chain.receive_signal(src_chain.uuid, send_signal_block_hash, signal_data, amount)
        send_signal_reward_block = dest_chain.send_signal_reward(receive_signal_block, src_chain.uuid, amount)
        receive_signal_reward_block = src_chain.receive_signal_reward(send_signal_reward_block.block_hash, dest_chain.uuid, amount)
        src_chain.accept_credit(amount, ref_block_hash=receive_signal_reward_block.block_hash)


class JSONLoader():

    def __init__(self, json_path):
        import os
        if not os.path.exists(json_path):
            raise Exception(f'Chain not found: {json_path}')

        self.json_path = json_path

    def load(self):
        import json
        with open(self.json_path, 'r') as f:
            chain = json.loads(f.read())

        verification_close_idx = {}
        try:
            with open(self.index_path(), 'r') as f:
                index = json.loads(f.read())
        except:
            pass
        else:
            for chain_uuid, serialized_block in index['verification_close_blocks'].items():
                verification_close_idx[chain_uuid] = self.init_block(serialized_block)

        return chain['uuid'], chain['seed'], self.init_blocks(chain['blocks']), verification_close_idx

    def save(self, chain_id, seed, blocks, verification_close_blocks):
        import json
        serialized_blocks = [block.serialize() for block in blocks]

        try:
            to_save = json.dumps({
                'uuid': str(chain_id),
                'seed': str(seed),
                'blocks': serialized_blocks
            }, indent=2)
        except Exception as e:
            print(serialized_blocks)
            raise

        with open(self.json_path, 'w') as f:
            f.write(to_save)

        serialized_close_blocks = {}
        for chain_id, block in verification_close_blocks.items():
            serialized_close_blocks[chain_id] = block.serialize()

        to_save = json.dumps({
            'verification_close_blocks': serialized_close_blocks
        }, indent=2)

        index_path = self.index_path()
        with open(index_path, 'w') as f:
            f.write(to_save)
            
        return True

    def index_path(self):
        import os
        path, ext = os.path.splitext(self.json_path)
        return os.path.join('%s%s%s' % (path, '_vcbidx', ext))

    def init_blocks(self, blocks):
        result = []

        for serialized_block in blocks:
            result.append(self.init_block(serialized_block))

        return result

    def init_block(self, serialized_block):
        block_type = serialized_block['block_type']

        if block_type == BlockType.SignalSent:
            return SignalSent(serialized_block)

        elif block_type == BlockType.SignalReceived:
            return SignalReceived(serialized_block)

        elif block_type == BlockType.SignalDelivered:
            return SignalDelivered(serialized_block)

        elif block_type == BlockType.SignalRewardSent:
            return SignalRewardSent(serialized_block)

        elif block_type == BlockType.SignalRewardReceived:
            return SignalRewardReceived(serialized_block)

        elif block_type == BlockType.Action:
            return Action(serialized_block)

        elif block_type == BlockType.WorkOutput:
            return WorkOutput(serialized_block)

        elif block_type == BlockType.Debit:
            return Debit(serialized_block)

        elif block_type == BlockType.Credit:
            return Credit(serialized_block)

        elif block_type == BlockType.CreditAccepted:
            return CreditAccepted(serialized_block)

        elif block_type == BlockType.CreditRejected:
            return CreditRejected(serialized_block)

        elif block_type == BlockType.TargetCreated:
            return TargetCreated(serialized_block)

        elif block_type == BlockType.TargetAccepted:
            return TargetAccepted(serialized_block)

        elif block_type == BlockType.TargetRewardClaimSent:
            return TargetRewardClaimSent(serialized_block)

        elif block_type == BlockType.TargetRewardClaimReceived:
            return TargetRewardClaimReceived(serialized_block)

        elif block_type == BlockType.TargetRewardSent:
            return TargetRewardSent(serialized_block)

        elif block_type == BlockType.TargetRewardReceived:
            return TargetRewardReceived(serialized_block)

        elif block_type == BlockType.WorkOutputRewardSent:
            return WorkOutputRewardSent(serialized_block)

        elif block_type == BlockType.WorkOutputRewardReceived:
            return WorkOutputRewardReceived(serialized_block)

        elif block_type == BlockType.AccessContractOwn:
            return AccessContractOwn(serialized_block)

        elif block_type == BlockType.AccessContractOther:
            return AccessContractOther(serialized_block)

        elif block_type == BlockType.AccessContractOwnEventAsk:
            return AccessContractOwnEventAsk(serialized_block)

        elif block_type == BlockType.AccessContractOtherEventOpen:
            return AccessContractOtherEventOpen(serialized_block)

        elif block_type == BlockType.AccessContractOtherEventClose:
            return AccessContractOtherEventClose(serialized_block)

        elif block_type == BlockType.VerificationOpen:
            return VerificationOpen(serialized_block)

        elif block_type == BlockType.Verification:
            return Verification(serialized_block)

        elif block_type == BlockType.VerificationClose:
            return VerificationClose(serialized_block)

        elif block_type == BlockType.Reset:
            return Reset(serialized_block)

        elif block_type == BlockType.Upgrade:
            return Upgrade(serialized_block)

        else:
            raise Exception('Unknown block encountered', serialized_block)


class Chain():
    version = 1

    seed = None # ChainSeed
    uuid = None # ChainID

    blocks = None
    data = None
    interface = None

    def __init__(self, interface, loader):
        # Dependency injection
        self.interface = interface
        self.loader = loader
        self.verification_close_block_index = {}

        try:
            self.load(loader)
        except Exception as e:
            import traceback; traceback.print_exc()
            raise Exception(f'Failed to load chain from {loader.json_path}')

    def delete(self):
        import os
        os.remove(self.loader.json_path)

    def load(self, loader=None):
        if not loader:
            loader = self.loader

        chain_uuid, chain_seed, blocks, verification_close_block_index = loader.load()

        self.uuid = chain_uuid
        self.seed = ChainSeed(chain_seed)
        self.blocks = blocks

        self.verification_close_block_index = verification_close_block_index

        return True

    def save(self, loader=None):
        return self.loader.save(self.uuid, self.seed, self.blocks, self.verification_close_block_index)

    def get_block_by_hash(self, block_hash):
        for block in self.blocks:
            if block.block_hash == block_hash:
                return block

    def get_block_idx_by_hash(self, block_hash):
        for i, block in enumerate(self.blocks):
            if block.block_hash == block_hash:
                return i

    def block_query(self, block_type, attr_query=None, window_far=None, window_near=None, multiple=False):
        if type(block_type) is list:
            multiple = True

        type_map = {
            'str': str,
            'int': int,
            'decimal': Decimal,
            'dict': dict,
        }

        result = []
        for block in self.blocks:
            block_matched = None

            if window_far or window_near:
                ts = block.ts
                if not ts:
                    continue

                if window_far and ts < window_far:
                    continue

                if window_near and ts > window_near:
                    continue

            if type(block_type) is list:
                if block.block_type not in block_type:
                    continue

            elif block.block_type != block_type:
                continue

            if attr_query:
                query_key = attr_query['key']
                query_subkey = attr_query.get('subkey')
                query_value = attr_query['value']
                query_value_type = attr_query['value_type']

                if not hasattr(block, query_key):
                    continue

                current_value = getattr(block, query_key)

                if query_subkey and query_key in block.dict_props:
                    try:
                        if '.' in query_subkey:
                            current_value = glom(current_value, query_subkey)
                        else:
                            current_value = current_value[query_subkey]
                    except:
                        pass

                if type(current_value) != type_map[query_value_type]:
                    continue

                if current_value == query_value:
                    block_matched = True

            else:
                block_matched = True

            if block_matched:
                if multiple:
                    result.append(block)
                else:
                    return block

        return result

    def send_signal(self, dest_chain_id, signal_data, amount=None):
        block = SignalSent()
        block.update(
            dest_chain_id=dest_chain_id,
            signal_data=signal_data,
            amount=amount
        )
        self.add_block(block)
        self.save()

        if self.interface:
            self.interface.send_signal(self.uuid, dest_chain_id, block.block_hash, signal_data, amount=amount)

        return block

    def receive_signal(self, src_chain_id, send_signal_block_hash, signal_data, amount=None, details=None):
        if type(amount) is not Decimal:
            amount = None

        if not amount or amount < 0:
            amount = None

        block = SignalReceived()
        block.update(
            src_chain_id=src_chain_id,
            send_signal_block_hash=send_signal_block_hash,
            signal_data=signal_data,
            amount=amount
        )
        self.add_block(block)
        self.save()

        return block

    def deliver_signal(self, src_chain_id, receive_signal_block_hash, activity_id, cost=None, amount=None):
        if type(amount) is not Decimal:
            amount = None

        if not amount or amount < 0:
            amount = None

        if not cost or type(cost) is not int or cost < 0:
            cost = 1

        block = SignalDelivered()
        block.update(
            src_chain_id=src_chain_id,
            receive_signal_block_hash=receive_signal_block_hash,
            activity_id=activity_id,
            cost=cost,
            amount=amount
        )
        self.add_block(block)
        self.save()

        return block

    def send_signal_reward(self, dest_chain_id, action_block_hash, deliver_signal_block_hash, amount, accepted_amount=None):
        assert type(amount) is Decimal
        assert amount > 0

        block = SignalRewardSent()
        block.update(
            dest_chain_id=dest_chain_id,
            action_block_hash=action_block_hash,
            deliver_signal_block_hash=deliver_signal_block_hash,
            amount=amount,
            accepted_amount=accepted_amount
        )
        self.add_block(block)
        self.save()

        return block

    def receive_signal_reward(self, src_chain_id, send_signal_reward_block_hash, amount):
        assert type(amount) is Decimal
        assert amount > 0

        block = SignalRewardReceived()
        block.update(
            src_chain_id=src_chain_id,
            send_signal_reward_block_hash=send_signal_reward_block_hash,
            amount=amount,
        )
        self.add_block(block)
        self.save()

        return block

    def add_action(self, action_id, activity_id, refs, deliver_signal_block_hash=None, timestamp=None):
        if not timestamp:
            import time
            timestamp = int(time.time())

        if not deliver_signal_block_hash:
            deliver_signal_block_hash = ''

        block = Action()
        block.update(
            action_id=action_id,
            activity_id=activity_id,
            timestamp=timestamp,
            refs=refs,
            deliver_signal_block_hash=deliver_signal_block_hash,
        )
        self.add_block(block)
        self.save()

        return block

    def add_work_output(self, action_id, activity_id, refs, details, timestamp=None):
        if not timestamp:
            import time
            timestamp = int(time.time())

        block = WorkOutput()
        block.update(
            action_id=action_id,
            activity_id=activity_id,
            timestamp=timestamp,
            refs=refs,
            details=details,
        )
        self.add_block(block)
        self.save()

        return block

    def add_target(self, name, target_id, reward_per, reward_pool, priors=None, conditions=None):
        assert type(reward_per) is Decimal
        assert type(reward_pool) is Decimal
        assert reward_per > 0
        assert reward_pool > 0
        assert reward_pool >= reward_per
        assert name
        assert len(name) <= 256

        if not priors:
            priors = []

        if not conditions:
            conditions = []

        block = TargetCreated()
        block.update(
            name=name,
            target_id=target_id,
            reward_per=reward_per,
            reward_pool=reward_pool,
            priors=priors,
            conditions=conditions,
        )
        self.add_block(block)
        self.save()

        return block

    def accept_target(self, src_chain_id, target_id, target_block_hash, target_details):
        block = TargetAccepted()
        block.update(
            src_chain_id=src_chain_id,
            #action_block_hash=action_block_hash,
            target_id=target_id,
            target_block_hash=target_block_hash,
            target_details=target_details
        )
        self.add_block(block)
        self.save()

        return block

    def send_target_reward_claim(self, dest_chain_id, target_block_hash, work_output_block_hash, work_output_details):
        block = TargetRewardClaimSent()
        block.update(
            dest_chain_id=dest_chain_id,
            target_block_hash=target_block_hash,
            work_output_block_hash=work_output_block_hash,
            work_output_details=work_output_details,
        )
        self.add_block(block)
        self.save()

        return block

    def receive_target_reward_claim(self, src_chain_id, target_block_hash, send_target_reward_claim_block_hash, work_output_block_hash, work_output_details):
        block = TargetRewardClaimReceived()
        block.update(
            src_chain_id=src_chain_id,
            target_block_hash=target_block_hash,
            send_target_reward_claim_block_hash=send_target_reward_claim_block_hash,
            work_output_block_hash=work_output_block_hash,
            work_output_details=work_output_details,
        )
        self.add_block(block)
        self.save()

        return block

    def send_target_reward(self, dest_chain_id, target_block_hash, receive_target_reward_claim_block_hash, amount):
        assert type(amount) is Decimal
        assert amount > 0

        block = TargetRewardSent()
        block.update(
            dest_chain_id=dest_chain_id,
            target_block_hash=target_block_hash,
            receive_target_reward_claim_block_hash=receive_target_reward_claim_block_hash,
            amount=amount,
        )
        self.add_block(block)
        self.save()

        return block

    def receive_target_reward(self, src_chain_id, target_block_hash, send_target_reward_block_hash, amount):
        assert type(amount) is Decimal
        assert amount > 0

        block = TargetRewardReceived()
        block.update(
            src_chain_id=src_chain_id,
            target_block_hash=target_block_hash,
            send_target_reward_block_hash=send_target_reward_block_hash,
            amount=amount,
        )
        self.add_block(block)
        self.save()

        return block

    def debit(self, amount, ref_block_hash=''):
        assert type(amount) is Decimal
        assert amount > 0

        if not ref_block_hash:
            ref_block_hash = ''

        block = Debit()
        block.update(
            balance_delta=-amount,
            ref_block_hash=ref_block_hash,
        )
        self.add_block(block)
        self.save()

        return block

    def accept_credit(self, amount, ref_block_hash=''):
        assert type(amount) is Decimal
        assert amount > 0

        if not ref_block_hash:
            ref_block_hash = ''

        block = CreditAccepted()
        block.update(
            balance_delta=amount,
            ref_block_hash=ref_block_hash,
        )
        self.add_block(block)
        self.save()

        return block

    def reject_credit(self, amount, ref_block_hash=''):
        assert type(amount) is Decimal
        block = CreditRejected()

        if not ref_block_hash:
            ref_block_hash = ''

        block.update(
            amount=amount,
            ref_block_hash=ref_block_hash,
        )
        self.add_block(block)
        self.save()

        return block

    def send_work_output_reward(self, dest_chain_id, amount, work_output_block_hash, details=None):
        assert amount > 0

        if not details:
            details = {}

        block = WorkOutputRewardSent()
        block.update(
            dest_chain_id=dest_chain_id,
            amount=amount,
            work_output_block_hash=work_output_block_hash,
            details=details,
        )
        self.add_block(block)
        self.save()

        return block

    def receive_work_output_reward(self, src_chain_id, amount, work_output_block_hash, send_work_output_reward_block_hash, details=None):
        assert amount > 0

        if not details:
            details = {}

        block = WorkOutputRewardReceived()
        block.update(
            src_chain_id=src_chain_id,
            amount=amount,
            work_output_block_hash=work_output_block_hash,
            send_work_output_reward_block_hash=send_work_output_reward_block_hash,
            details=details,
        )
        self.add_block(block)
        self.save()

        return block

    def add_access_contract_own(self, dest_chain_id, contract_amount, token, node_uuid, frame_uuid, expires_in, min_price, details=None):
        assert contract_amount > 0
        assert min_price > 0

        if not details:
            details = {}

        block = AccessContractOwn()
        block.update(
            dest_chain_id=dest_chain_id,
            contract_amount=contract_amount,
            token=token,
            node_uuid=node_uuid,
            frame_uuid=frame_uuid,
            expires_in=expires_in,
            min_price=min_price,
            details=details,
        )
        self.add_block(block)
        self.save()

        return block

    def add_access_contract_other(self, src_chain_id, access_contract_block_hash, contract_amount, token, contract_ts, expires_in, min_price, details=None):

        assert contract_amount > 0
        assert min_price > 0
        assert contract_ts > 0

        if not details:
            details = {}

        block = AccessContractOther()
        block.update(
            src_chain_id=src_chain_id,
            access_contract_block_hash=access_contract_block_hash,
            contract_amount=contract_amount,
            token=token,
            contract_ts=contract_ts,
            expires_in=expires_in,
            min_price=min_price,
            details=details,
        )
        self.add_block(block)
        self.save()

        return block

    def add_access_contract_own_event(self, dest_chain_id, event_amount):
        assert event_amount > 0

        if not details:
            details = {}

        block = AccessContractOwnEvent()
        block.update(
            dest_chain_id=dest_chain_id,
            event_amount=event_amount,
        )
        self.add_block(block)
        self.save()

        return block

    def add_access_contract_other_event_open(self, access_contract_block_hash, other_access_contract_block_hash, event_amount, details=None):
        assert event_amount > 0

        if not details:
            details = {}

        block = AccessContractOtherEventOpen()
        block.update(
            access_contract_block_hash=access_contract_block_hash,
            other_access_contract_block_hash=other_access_contract_block_hash,
            amount=event_amount,
            details=details,
        )
        self.add_block(block)
        self.save()

        return block

    def add_access_contract_own_event_ask(self, access_contract_block_hash, other_event_open_block_hash, receive_signal_block_hash, event_amount, details=None):
        assert event_amount > 0

        if not details:
            details = {}

        block = AccessContractOwnEventAsk()
        block.update(
            access_contract_block_hash=access_contract_block_hash,
            other_event_open_block_hash=other_event_open_block_hash,
            receive_signal_block_hash=receive_signal_block_hash,
            amount=event_amount,
            details=details,
        )
        self.add_block(block)
        self.save()

        return block

    def add_access_contract_other_event_close(self, access_contract_block_hash, other_access_contract_block_hash,
                                        access_contract_event_block_hash, other_access_contract_event_block_hash,
                                        receive_signal_reward_block_hash):

        block = AccessContractOtherEventClose()
        block.update(
            access_contract_block_hash=access_contract_block_hash,
            other_access_contract_block_hash=other_access_contract_block_hash,
            access_contract_event_block_hash=access_contract_event_block_hash,
            other_access_contract_event_block_hash=other_access_contract_event_block_hash,
            receive_signal_reward_block_hash=receive_signal_reward_block_hash,
        )
        self.add_block(block)
        self.save()

        return block

    def generate_seed_hash(self):
        import hashlib
        seed_hash = hashlib.sha256(str(self.seed).encode('utf-8')).hexdigest()
        return seed_hash

    def add_block(self, block):
        head_block = self.head_block()
        if head_block.is_type(BlockType.Null):
            prev_block_hash = self.generate_seed_hash()
            height = 1
        else:
            prev_block_hash = head_block.block_hash
            height = head_block.height + 1

        balance = head_block.balance
        if block.balance_delta != 0:
            balance += block.balance_delta

        block.prev_block_hash = prev_block_hash
        block.height = height
        block.balance = balance
        block.generate_hash()

        self.blocks.append(block)

        if block.block_type == BlockType.VerificationClose:
            self.index_verification_close_block(block)

    def head_block(self):
        if not self.blocks:
            return NullBlock()

        return self.blocks[-1:][0]

    def balance(self):
        return self.head_block().balance

    def make_valid(self):
        # Restore local integrity to the chain.
        #   Cannot fix references to other chains.
        #   Cannot fix problems in contained data.

        result = self.find_invalid()
        if result is True:
            return True
        else:
            invalid_block, idx = result

        max_iterations = len(self.blocks)
        i = 0

        while i <= max_iterations:
            i += 1

            prev_block = self.blocks[idx - 1]

            invalid_block.balance = prev_block.balance + invalid_block.balance_delta
            invalid_block.prev_block_hash = prev_block.block_hash
            invalid_block.generate_hash()

            # Efficiency be damned: verify() starts from the beginning each time.
            result = self.find_invalid()
            if result is True:
                return True
            else:
                next_invalid_block, next_idx = result
                if next_invalid_block == invalid_block:
                    print('Rebuild failed', next_invalid_block, invalid_block)
                    raise Exception(f'Rebuild failed on block {invalid_block.block_hash}, idx={idx}')
                else:
                    invalid_block = next_invalid_block
                    idx = next_idx

        return False

    def verify(self, quiet=True, exc=True):
        
        # Iterate blocks from bottom (head, newest) to top (tail, oldest)

        next_block_hash = None
        for idx in range(len(self.blocks) - 1, -1, -1):
            block = self.blocks[idx]

            if next_block_hash:
                # Stored prev_hash on later block matches stored hash of current block
                if next_block_hash != block.block_hash:
                    msg = f'Chain verification failed on block {block.block_hash} ({idx})'
                    if exc:
                        raise Exception(msg)
                    else:
                        print(msg)
                        print(next_block_hash, block.block_hash)
                        return block, idx

            # Own hash matches
            try:
                block.validate_hash()
            except Exception as e:
                if exc:
                    raise
                else:
                    return block, idx

            next_block_hash = block.prev_block_hash

            if idx == 0:
                if next_block_hash != self.generate_seed_hash():
                    if exc:
                        msg = f'Chain verification failed on origin block {block.block_hash} ({idx})'
                        print(msg)
                        raise Exception(msg)
                    else:
                        return block, idx
            
            if not quiet:
                print('Block %d valid' % idx)

        return True

    def find_invalid(self):
        # Find the earliest invalid block
        # Iterate blocks from top (tail, oldest) to bottom (head, newest)

        prev_block_hash = None
        for idx, block in enumerate(self.blocks):
            # Own hash matches

            if idx == 0:
                if block.prev_block_hash != self.generate_seed_hash():
                    return block, idx
            else:
                try:
                    block.validate_hash()
                except Exception as e:
                    return block, idx

            if prev_block_hash:
                if prev_block_hash != block.prev_block_hash:
                    return block, idx

            prev_block_hash = block.block_hash

        return True

    def get_linked_blocks(self, other_chain_id, as_list=False):
        linked_blocks = {
            BlockType.SignalSent: {},
            BlockType.SignalReceived: {},
            BlockType.SignalRewardSent: {},
            BlockType.SignalRewardReceived: {}
        }

        block_list = []
        for block in self.blocks:
            if block.block_type not in linked_blocks.keys():
                continue

            if block.block_type in (BlockType.SignalSent, BlockType.SignalRewardSent):

                if block.dest_chain_id == other_chain_id:
                    linked_blocks[block.block_type][block.block_hash] = block
                    block_list.append(block)

            elif block.block_type in (BlockType.SignalReceived, BlockType.SignalRewardReceived):

                if block.src_chain_id == other_chain_id:
                    linked_blocks[block.block_type][block.block_hash] = block
                    block_list.append(block)

        if as_list:
            return block_list
        else:
            return linked_blocks

    def cross_verify(self, other_chain, quiet=True):

        # Extract only the blocks that relate to the other chain
        self_linked_blocks = self.get_linked_blocks(other_chain.uuid)
        other_linked_blocks = other_chain.get_linked_blocks(self.uuid)

        # All SignalReceived blocks this chain must map to a SignalSent block in the other chain

        # The list of originating hashes for all received signals.
        self_sig_rec_block_ids = []
        for block in self_linked_blocks[BlockType.SignalReceived].values():
            self_sig_rec_block_ids.append(block.send_signal_block_hash)

        num_sig_rec_blocks = len(self_sig_rec_block_ids)
        if num_sig_rec_blocks > 0:
            other_sig_sent_block_ids = other_linked_blocks[BlockType.SignalSent].keys()

            # Find all the pairs by intersecting what this chain knows with what the other chain knows.
            mapped_blocks = set(self_sig_rec_block_ids) & set(other_sig_sent_block_ids)

            print(sorted(list(self_sig_rec_block_ids)))
            print(sorted(list(other_sig_sent_block_ids)))

            # If there is a different amount of pairs than what we know about, it's a problem
            if len(mapped_blocks) != num_sig_rec_blocks:
                print(len(mapped_blocks), num_sig_rec_blocks)
                print(sorted(mapped_blocks), sorted(self_sig_rec_block_ids))
                raise Exception('Signal verification failed')
        else:
            if not quiet:
                print(f'No signal-received blocks on chain {self.uuid}')
        
        # All SignalRewardReceived blocks this chain must map to a SignalRewardSent block in the other chain
        self_rew_rec_block_ids = []
        for block in self_linked_blocks[BlockType.SignalRewardReceived].values():
            self_rew_rec_block_ids.append(block.send_signal_reward_block_hash)

        if len(self_rew_rec_block_ids) > 0:
            other_rew_sent_block_ids = other_linked_blocks[BlockType.SignalRewardSent].keys()
            mapped_blocks = set(self_rew_rec_block_ids) & set(other_rew_sent_block_ids)

            if len(mapped_blocks) != len(self_rew_rec_block_ids):
                raise Exception('Reward verification failed')
        else:
            if not quiet:
                print(f'No reward-received blocks on chain {self.uuid}')

        print(f'Cross-verification from chain {self.uuid} to chain {other_chain.uuid} succeeded')
        return True

    def get_verification_block(self, src_chain_id, begin_idx=None):
        verification_block = None

        if begin_idx is None:
            begin_idx = len(self.blocks) - 1

        # Iterate from top to bottom
        for idx in range(begin_idx, -1, -1):
            block = self.blocks[idx]
            if block.block_type == BlockType.Verification:
                if block.src_chain_id == src_chain_id:
                    verification_block = block
                    break

        if not verification_block:
            idx = None

        return verification_block, idx

    def get_verification_close_block(self, dest_chain_id, begin_idx=None):
        verification_block = None

        if begin_idx is None:
            begin_idx = len(self.blocks) - 1

        # Iterate from top to bottom
        for idx in range(begin_idx, -1, -1):
            block = self.blocks[idx]
            if block.block_type == BlockType.VerificationClose:
                if block.dest_chain_id == dest_chain_id:
                    verification_block = block
                    break

        if not verification_block:
            idx = None

        return verification_block, idx

    def get_verification_close_blocks(self, ignore_chain_id=None):
        close_blocks = []
        for block in self.blocks:
            if block.block_type == BlockType.VerificationClose:
                if not ignore_chain_id or block.dest_chain_id != ignore_chain_id:
                    close_blocks.append(block)

        return close_blocks

    def get_verification_subchain(self, verification_block, begin_idx, other_chain_id):
        sub_chain = []

        # Iterate from top to bottom
        for idx in range(begin_idx, -1, -1):
            block = self.blocks[idx]
            if self.block_in_verification(block, other_chain_id):
                sub_chain.append(block)

        return sub_chain

    def block_in_verification(self, block, other_chain_id):
        sub_block = None

        if block.block_type == BlockType.Verification:
            if block.src_chain_id == other_chain_id:
                sub_block = block
        elif block.block_type in (BlockType.SignalSent, BlockType.SignalRewardSent):
            if block.dest_chain_id == other_chain_id:
                sub_block = block
        elif block.block_type in (BlockType.SignalReceived, BlockType.SignalRewardReceived):
            if block.src_chain_id == other_chain_id:
                sub_block = block

        return sub_block

    def compute_validation_subchain(self, sub_chain):
        sub_chain_balance = Decimal('0')
            
        from hashlib import sha256
        sub_chain_hash = sha256()

        sub_chain = sub_chain[:]
        sub_chain.reverse()
        for block in sub_chain:
            sub_chain_balance += block.balance_delta
            sub_chain_hash.update(block.block_hash.encode('utf-8'))

        return sub_chain_balance, sub_chain_hash.hexdigest()

    def get_stats(self):
        stats = {
            'Balance': str(self.balance()),
            'NumBlocks': len(self.blocks),
        }

        return stats

    def index_verification_close_block(self, verification_close_block):
        if verification_close_block.block_type != BlockType.VerificationClose:
            return

        chain_id = verification_close_block.dest_chain_id
        existing_block = self.verification_close_block_index.get(chain_id)

        if not existing_block or existing_block.height < verification_close_block.height:
            self.verification_close_block_index[chain_id] = verification_close_block

        self.save()

    def get_credibility(self, other_chain_id=None, minimal=False):
        chain = self

        dest_block_types = (
            BlockType.TargetRewardSent,
            BlockType.SignalSent,
            BlockType.SignalRewardSent,
            BlockType.WorkOutputRewardSent,
            BlockType.AccessContractOwn,
        )
        
        src_block_types = (
            BlockType.TargetRewardReceived,
            BlockType.SignalRewardReceived,
            BlockType.SignalReceived,
            BlockType.WorkOutputRewardReceived,
            BlockType.AccessContractOther,
        )

        credit_stats = defaultdict(lambda: {
            'Balance': Decimal('0'),
            'Debit': Decimal('0'),
            'Credit': Decimal('0'),
            'TotalVerified': Decimal('0'),
            'TotalOtherVerified': Decimal('0'),
            'Blocks': []
        })

        for block in chain.blocks:
            
            if block.block_type == BlockType.Debit:
                ref_block_hash = block.ref_block_hash
                if not ref_block_hash:
                    continue

                ref_block = chain.get_block_by_hash(ref_block_hash)

                if not ref_block:
                    print('Missing ref for', BlockTypeMap[block.block_type], block)
                    continue

                if ref_block.block_type in dest_block_types:
                    if other_chain_id and ref_block.dest_chain_id != other_chain_id:
                        continue

                    credit_stats[ref_block.dest_chain_id]['Debit'] += block.balance_delta

                    if not minimal:
                        credit_stats[ref_block.dest_chain_id]['Blocks'].append({
                            'BlockType': block.block_type,
                            'BlockHash': block.block_hash,
                            'Amount': block.balance_delta,
                            'RefBlockType': ref_block.block_type,
                            'RefBlockHash': block.ref_block_hash,
                        })

            elif block.block_type == BlockType.CreditAccepted:
                ref_block_hash = block.ref_block_hash
                if not ref_block_hash:
                    continue

                ref_block = chain.get_block_by_hash(ref_block_hash)

                if not ref_block:
                    print('Missing ref for', BlockTypeMap[block.block_type], block)
                    continue

                if ref_block.block_type in src_block_types:
                    if other_chain_id and ref_block.src_chain_id != other_chain_id:
                        continue

                    credit_stats[ref_block.src_chain_id]['Credit'] += block.balance_delta

                    if not minimal:
                        credit_stats[ref_block.src_chain_id]['Blocks'].append({
                            'BlockType': block.block_type,
                            'BlockHash': block.block_hash,
                            'Amount': block.balance_delta,
                            'RefBlockType': ref_block.block_type,
                            'RefBlockHash': block.ref_block_hash,
                        })

            elif block.block_type == BlockType.SignalRewardSent:
                # Special case because this is how currency is mined

                if other_chain_id and block.dest_chain_id != other_chain_id:
                    continue

                credit_stats[block.dest_chain_id]['Credit'] += block.amount
                if not minimal:
                    credit_stats[block.dest_chain_id]['Blocks'].append({
                        'BlockType': block.block_type,
                        'BlockHash': block.block_hash,
                        'Amount': block.amount,
                    })

            elif block.block_type == BlockType.Verification:

                if other_chain_id and block.src_chain_id != other_chain_id:
                    continue

                credit_stats[block.src_chain_id]['TotalVerified'] += block.sub_chain_balance

            elif block.block_type == BlockType.VerificationClose:
                credit_stats[block.dest_chain_id]['TotalOtherVerified'] += block.sub_chain_balance

        for chain_uuid in credit_stats:
            credit_stats[chain_uuid]['Balance'] = credit_stats[chain_uuid]['Debit'] + credit_stats[chain_uuid]['Credit']

        return credit_stats

    def confirm_verify(self, other_chain):
        chain = self

        # For now, find and confirm every block
        # Later, could start at a specific block and continue N deep

        # Find the next verification block
        verification_block, block_idx = chain.get_verification_block(other_chain.uuid)

        if verification_block:
            verification_subchain = chain.get_verification_subchain(verification_block, block_idx - 1, other_chain.uuid)

            # Recalculate the verification sub-chain details
            sub_chain_balance, sub_chain_hash = chain.compute_validation_subchain(verification_subchain)

            if sub_chain_hash == verification_block.sub_chain_hash:
                print('Sub chain verified')
                return True
            else:
                print('Sub chain verification failed')
                return False

        else:
            print('No verification block found')
            return None

    def hard_verify(self, other_chain):
        chain = self

        # Add a 'was verified by chain 2' block to chain 1
        # Add a 'verified chain 1' block to chain 2

        # Get key stats:
        #     - current block height of chain 1
        #     - current balance of chain 1
        #     - number of chain 2 blocks in chain 1
        #     - total balance of all chain 2 blocks in chain 1
        
        #     - number of chain 2 blocks in latest sub-chain
        #     - total balance of chain 2 blocks latest sub-chain
        
        #     - hash of last time chain 2 verified chain 1 (if any)
        #     - block height of the previous verify block
        #     - hash-chain of the sub-chain being verified (including last verification block)
        #     - flag for whether a full verification was done?

        # 1. Find the most recent verification block, if any.
        #       This could be cached/indexed in the future

        # 2. Get key pieces of data

        sub_chain = []
        sub_chain_balance = Decimal('0')
        
        from hashlib import sha256
        sub_chain_hash = sha256()

        prev_verification_block = None
        # Iterate from top to bottom
        for idx in range(len(chain.blocks) - 1, -1, -1):
            block = chain.blocks[idx]
            if block.block_type == BlockType.Verification:
                if block.src_chain_id == other_chain.uuid:
                    prev_verification_block = block
                    break

        chain_length = len(chain.blocks)
        begin_idx = 0
        prev_verification_block_hash = None
        if prev_verification_block:
            begin_idx = idx
            prev_verification_block_hash = prev_verification_block.block_hash

        # Iterate from bottom or latest verification block to top.
        for idx in range(begin_idx, chain_length):
            block = chain.blocks[idx]
            new_block = chain.block_in_verification(block, other_chain.uuid)

            if new_block:
                sub_chain.append(block)
                sub_chain_balance += block.balance_delta
                sub_chain_hash.update(block.block_hash.encode('utf-8'))

        sub_chain_length = len(sub_chain)

        other_block_open = VerificationOpen()
        other_block_open.update(
            dest_chain_id=chain.uuid
        )
        other_chain.add_block(other_block_open)
        other_chain.save()

        new_verification_block = None
        other_block_close = None

        if sub_chain_length > 1:
            print(f'Previous verification block: {prev_verification_block}')
            print(f'Current block height of chain 1: {chain_length}')
            print(f'Current balance of chain 1: {chain.balance()}')
            print(f'Number of chain 2 blocks in chain 1: {sub_chain_length}')
            print(f'Total balance of all chain 2 blocks in chain 1: {sub_chain_balance}')
            print(f'Hash-chain of the sub-chain being verified (including last verification block): {sub_chain_hash.hexdigest()}')
            print(f'Flag for whether a full verification was done: True')

            other_verification_block_hash = other_block_open.block_hash
            full_verification = True

            new_verification_block = Verification()
            new_verification_block.update(
                src_chain_id=other_chain.uuid,
                prev_verification_block_hash=prev_verification_block_hash,
                other_verification_block_hash=other_verification_block_hash,
                
                chain_length=chain_length,

                sub_chain_balance=sub_chain_balance,
                sub_chain_length=sub_chain_length,
                sub_chain_hash=sub_chain_hash.hexdigest(),
                
                full_verification=full_verification
            )
            chain.add_block(new_verification_block)
            chain.save()

            other_block_close = VerificationClose()
            other_block_close.update(
                dest_chain_id=chain.uuid,
                open_verification_block_hash=other_block_open.block_hash,
                other_verification_block_hash=new_verification_block.block_hash,
                
                chain_length=chain_length,

                sub_chain_balance=sub_chain_balance,
                sub_chain_length=sub_chain_length,
                sub_chain_hash=sub_chain_hash.hexdigest(),
                
                full_verification=full_verification
            )
            other_chain.add_block(other_block_close)
            other_chain.save()

        else:
            print('Nothing to do.')

        # Trade VerificationClose blocks between the chains

        # Pull from other chain
        verification_close_blocks = other_chain.get_verification_close_blocks(ignore_chain_id=chain.uuid)
        if len(verification_close_blocks):
            print(f'Pulled {len(verification_close_blocks)} VerificationClose blocks from {other_chain.uuid}')
        else:
            print(f'Pulled no VerificationClose blocks from {other_chain.uuid}')

        for verification_close_block in verification_close_blocks:
            chain.index_verification_close_block(verification_close_block)

        for verification_close_block in other_chain.verification_close_block_index.values():
            chain.index_verification_close_block(verification_close_block)

        print(len(chain.verification_close_block_index.keys()))

        # Push to other chain
        verification_close_blocks = chain.get_verification_close_blocks(ignore_chain_id=other_chain.uuid)
        if len(verification_close_blocks):
            print(f'Pushed {len(verification_close_blocks)} VerificationClosed blocks to {chain.uuid}')
        else:
            print(f'Pushed no VerificationClose blocks to {chain.uuid}')

        for verification_close_block in verification_close_blocks:
            other_chain.index_verification_close_block(verification_close_block)

        for verification_close_block in chain.verification_close_block_index.values():
            other_chain.index_verification_close_block(verification_close_block)

        print(len(other_chain.verification_close_block_index.keys()))

        return {
            'verified': new_verification_block is not None,
            'chain': {
                'uuid': chain.uuid,
                'verification_block': new_verification_block
            },
            'other_chain': {
                'uuid': other_chain.uuid,
                'open_block': other_block_open,
                'close_block': other_block_close,
            }
        }


def init_chain(chain_uuid=None):
    import os
    import json
    from uuid import uuid4

    if not chain_uuid:
        chain_uuid = str(uuid4())

    from config import config

    chain_path = config['DUO_CHAIN_PATH']
    chain_file = f'{chain_path}/chain_{chain_uuid}.json'

    if os.path.exists(chain_file):
        raise Exception('Chain already exists')

    with open(chain_file, 'w') as f:
        f.write(json.dumps({
            'uuid': str(chain_uuid),
            'seed': f'seed-{chain_uuid}',
            'blocks': []
        }, indent=2))

    interface = None
    chain = Chain(interface, JSONLoader(chain_file))

    return chain


chain_cache = {}

def get_chain(chain_uuid: str, cache_ttl=None):
    import os
    import json
    import time

    if cache_ttl:
        cached_chain = chain_cache.get(chain_uuid)
        if cached_chain:
            if time.time() - cached_chain['ts'] < cache_ttl:
                return cached_chain['chain']

    from config import config

    chain_path = config['DUO_CHAIN_PATH']
    chain_file = f'{chain_path}/chain_{chain_uuid}.json'

    if not os.path.exists(chain_file):
        raise Exception(f'Chain not found: {chain_file}')

    interface = None
    chain = Chain(interface, JSONLoader(chain_file))

    chain_cache[chain_uuid] = {
        'ts': time.time(),
        'chain': chain
    }

    return chain


def get_chains(chain_path: str = './chains'):
    import os
    import json

    if not os.path.exists(chain_path):
        raise Exception(f'Path not found: {chain_path}')

    chains = []
    interface = None

    import glob
    search = os.path.join(chain_path, 'chain*.json')
    for chain_file in glob.glob(search):
        if '_vcbidx' in chain_file:
            continue

        try:
            chains.append(Chain(interface, JSONLoader(chain_file)))
        except Exception as e:
            print(f'Error loading chain file : {e}')
        else:
            print(f'Loaded chain file {chain_file}')

    return chains
