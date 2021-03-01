

from doorbot.overlays import OverlayHandler

class Motion( OverlayHandler ):

    def draw( self, frame, **kwargs ):

        events = kwargs['event'] if 'event' in kwargs else []

        for event in events:
            # TODO: Vary color based on type of object.
            color = (255, 0, 0)
            box = {
                'x1': event.position[0], 'y1': event.position[1],
                'x2': event.position[0] + event.dimensions[0],
                'y2': event.position[1] + event.dimensions[1],
                'color': color
            }

            self.master.rect( frame,
                (box['x1'], box['y1']),
                (box['x2'], box['y2']), box['color'], 3 )
