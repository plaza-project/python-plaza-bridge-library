from .blocks import (BlockArgument, BlockContext, CallbackBlockArgument,
                     CollectionBlockArgument, VariableBlockArgument)
from .bridge import PlazaBridge
from .registration import (FormBasedServiceRegistration,
                           MessageBasedServiceRegistration)

import sys
print('*** `plaza-bridge` is no longer maintaned. Please install the `programaker-bridge` package instead. ***\n',
      file=sys.stderr)
