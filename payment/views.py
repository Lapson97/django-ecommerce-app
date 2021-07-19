import braintree
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from paypal.standard.forms import PayPalPaymentsForm
from orders.models import Order
from .tasks import payment_completed


# instantiate Braintree payment gateway
gateway = braintree.BraintreeGateway(settings.BRAINTREE_CONF)


def payment_process(request):
    order_id = request.session.get('order_id')
    order = get_object_or_404(Order, id=order_id)
    total_cost = order.get_total_cost()
    host = request.get_host()

    paypal_dict = {
        'business': settings.PAYPAL_RECEIVER_EMAIL,
        'amount': '%.2f' % total_cost.quantize(Decimal('.01')),
        'item_name': f'Order {order.id}',
        'invoice': str(order.id),
        'currency_code': 'USD',
        'notify_url': f'http://{host}{reverse("paypal-ipn")}',
        'return_url': f'http://{host}{reverse("payment:done")}',
        'cancel_return': f'http://{host}{reverse("payment:canceled")}',
    }
    form = PayPalPaymentsForm(initial=paypal_dict)
    order.paid = True
    order.save()
    # launch asynchronous task
    payment_completed.delay(order.id)
    return render(request, 'payment/process.html', {'order': order, 'form': form})

    # if request.method == 'POST':
    #     # retrieve nonce
    #     nonce = request.POST.get('payment_method_nonce', None)
    #     # create and submit transaction
    #     result = gateway.transaction.sale({
    #         'amount': f'{total_cost:.2f}',
    #         'payment_method_nonce': nonce,
    #         'options': {
    #             'submit_for_settlement': True
    #         }
    #     })
    #     if result.is_success:
    #         # mark the order as paid
    #         order.paid = True
    #         # store the unique transaction id
    #         order.braintree_id = result.transaction.id
    #         order.save()
    #         return redirect('payment:done')
    #     else:
    #         return redirect('payment:canceled')
    # else:
    #     # generate token
    #     client_token = gateway.client_token.generate()
    #     return render(request,
    #                   'payment/process.html',
    #                   {'order': order,
    #                    'client_token': client_token})


@csrf_exempt
def payment_done(request):
    return render(request, 'payment/done.html')


@csrf_exempt
def payment_canceled(request):
    return render(request, 'payment/canceled.html')
