## Description

This is the engine I use to backtest my strategies. As I use IBKR's API and [ib_insync](https://github.com/erdewit/ib_insync)
to access markets, the library re-uses some of the objects available in there.

I've tried to keep the whole thing as simple as possible. The components are:
+ a strategy interface with 5 methods to implement. Four of them (`on_pending_tickers_event`, `on_pnl_single_event`...) are called by the backtester every time an event of that type happens.
+ a market (one for each contract) that reads ticks from a database and passes them to the backtester, it does also serve as matching engine.
+ a backtester that coordinates the whole thing

This repo is meant to be installed as a library. An example of usage can be found in this
companion repo [simple_strategy](github.com/gipaetusb/SimpleStrategy).

## Install
`pip install git+ssh://git@github.com/gipaetusb/SimpleBacktester#egg=simplebt`

Credit to Arocketman for his post: [link](https://medium.com/@arocketman/creating-a-pip-package-on-a-private-repository-using-setuptools-fff608471e39)