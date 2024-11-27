# DUO

DUO is a *seriously different kind of blockchain*.

Ditch everything you think you know about blockchains and digital currency. You'll need fresh eyes here.

DUO is designed to *actually, measurably help* our civilization bridge the vast chasms between our seemingly-dire situations today and our hopes for the future. It works one human at a time. Well, more like two humans at a time. Hence the name: DUO.

That's right, DUO is a dyadic blockchain. It is fundamentally pairwise: you and someone else. And yet it bootstraps itself somehow? See if you can figure that one out.

A few other differences:

- Everyone gets their own blockchain
- There is no global blockchain
- No blockchain *needs* to know about any other
- You can edit your own DUO blockchain willy-nilly
- If you see someone else's blockchain, go ahead and edit that one willy-nilly too
- It is entirely credit driven, like fiat
- Its "proof of work" is fundamentally valuable
- It perpetuates itself through the exchange of legitimate value (no hype-artists needed)

And that's not all. Some people refer to it as *Laissez-Faire Fiat*.

Take this opportunity to remind yourself that DUO is a serious project. It's not a joke, it's just very different than usual.

Yes, it could be *wrong* and it might be *stupid*. Yes, it could be *unfit for purpose*. Heck, it could be *dangerous*. But if it happens to be different in the right direction? Then it may inspire the thing that *works wonderfully*. And who friggin knows what that might look like.

<!--
DUO is designed to be the spine of a civilization-scale permanent memory.

When you're serious about the future, this is the kind of permanent memory you'll converge on.

Prediction: The more seriously we contemplate the future of digital-era humanity, the more we'll converge on DUO or something like it.
-->

## About this public release

DUO is soft and squishy like a teddy bear and wants to stay that way.

***NEVER EXPOSE DUO TO THE OPEN INTERNET***

This public release is DUO's first reference implementation. Think of it as proof of life. Presumably it'll improve.

After looking at it for a while, you may notice that it makes no sense for DUO to stand alone like this. It is one side of a coin; the other half isn't here, man.

### Setup up the environment

	mkdir -p data/chains
	python3 -m venv env
	env/bin/pip3 install -r requirements.txt

### Start the DUO server

Start up on port 7012

	env/bin/uvicorn server:app --port 7012

Test that it's working:

	curl http://localhost:7012/state

If your setup is good you'll see:

	{"Origin":"DUO","Chains":[]}

God help you if you see anything else.

### Play away

The rest of the API can be found in server.py

Now go forth and multiply!
