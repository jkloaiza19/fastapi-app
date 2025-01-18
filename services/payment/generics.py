# from typing import List, Optional, Generic
#
#
# class Stack[T]:
#     def __init__(self) -> None:
#         self._container: List[T] = []
#
#     def __str__(self) -> str:
#         return str(self._container)
#
#     def push(self, item: T) -> None:
#         self._container.append(item)
#
#     def pop(self) -> T:
#         return self._container.pop()
#
#     def is_empty(self):
#         return self._container == []
#
#     def peek(self) -> Optional[T]:
#         if self.is_empty():
#             return None
#         return self._container[-1]
#
#     def size(self) -> int:
#         return len(self._container)
#
#
