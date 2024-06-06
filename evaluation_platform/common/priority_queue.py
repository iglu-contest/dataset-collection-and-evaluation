from collections import defaultdict


class PriorityQueue:
    def __init__(self) -> None:
        self._queues = defaultdict(list)
        self.highest_priority = 0
        self.lowest_priority = 0
        self._element_to_priority = {}

    @property
    def size(self):
        return len(self._element_to_priority)

    def enqueue(self, element, priority=None):
        if priority is None:
            priority = self.lowest_priority
        self._element_to_priority[element] = priority
        self._queues[priority].append(element)
        self.lowest_priority = max(self.lowest_priority, priority)
        if self.size > 1:
            self.highest_priority = min(self.highest_priority, priority)
        else:
            self.highest_priority = priority

    def dequeue(self):
        element = None
        if self.size == 0:
            return element

        element = self._queues[self.highest_priority].pop(0)
        self._element_to_priority.pop(element)
        if len(self._queues[self.highest_priority]) == 0:
            self._queues.pop(self.highest_priority)
            self._update_highest_priority()
        return element

    def _update_highest_priority(self):
        if self.size == 0:
            self.highest_priority = 0
        else:
            self.highest_priority = min(self._element_to_priority.values())

    def get_queue(self, priority: int):
        return self._queues[priority]

    def contains(self, element, priority=None) -> bool:
        """Search for element in queues. If priority is None, search all queues

        Args:
            element (Any): element to search
            priority (int, optional): Specific priority to search. Defaults to None.
        """
        if priority is not None:
            if priority not in self._queues:
                return False
            return element in self._queues[priority]
        return element in self._element_to_priority
