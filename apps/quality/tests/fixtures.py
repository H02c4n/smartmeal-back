"""Quality test yardımcıları."""
from apps.production.tests.fixtures import make_batch_with_order_line


def make_batch():
    return make_batch_with_order_line(quantity=1)