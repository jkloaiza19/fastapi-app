from abc import ABC, abstractmethod
from dataclasses import dataclass


class ContractInterface(ABC):
    @abstractmethod
    def calculate_hourly_rate(self):
        pass


@dataclass
class Contract(ContractInterface):
    hourly_rate: int
    commission: int

    def calculate_hourly_rate(self):
        return self.hourly_rate + self.commission


def main():
    if __name__ == "__main__":
        contract = Contract(hourly_rate=100, commission=10)
