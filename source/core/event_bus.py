class EventBus:

    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type, module):

        if event_type not in self.subscribers:
            self.subscribers[event_type] = []

        self.subscribers[event_type].append(module)

    def publish(self, event):

        if event.type not in self.subscribers:
            return

        for module in self.subscribers[event.type]:
            module.handle_event(event)