from abc import ABC, abstractmethod
from typing import List, Union
from simplebt.events import StrategyTrade, Event, ChangeBestBatch, MktTradeBatch


class StrategyInterface(ABC):
    """
    This class defines the architecture of the Strategy.
    This class will have a concrete form for every different Strategy we want to write.
    """

    @abstractmethod
    def process_event(self, event: Union[Event, List[Event]]):
        """
        Practically a scala pattern match case
        Process a single event or a list of events (since we might receive 'em in batches)
        and forward them to the appropriate method
        """
        raise NotImplementedError

    # @abstractmethod
    # def on_book_creation(self, book: Book) -> None:
    #     """
    #     Series of actions to be done when the first book is created.
    #     """
    #     pass

    @abstractmethod
    def on_change_best(self, event: ChangeBestBatch):
        """
        Series of actions to be done when the first level of a book changes.
        """
        raise NotImplementedError
    
    @abstractmethod
    def on_strategy_trade(self, event: StrategyTrade):
        """
        Series of actions to be done when there is a proprietary trade.
        """
        raise NotImplementedError

    @abstractmethod
    def on_market_trade(self, event: MktTradeBatch):
        """
        Series of actions to be done when there is a trade in the market.
        """
        raise NotImplementedError