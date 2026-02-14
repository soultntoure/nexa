<script setup lang="ts">
useHead({ title: 'Withdrawal - Nexa' })

const {
  accounts,
  loadingAccounts,
  selectedMethod,
  selectedAccount,
  amount,
  recipientName,
  recipientAccount,
  isSubmitting,
  showSuccess,
  showFraudNotice,
  evalResult,
  currentAccount,
  parsedAmount,
  calculatedFee,
  receiveAmount,
  amountError,
  canSubmit,
  handleSubmit,
  dismissResult,
} = useWithdrawal()
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Request Withdrawal</h1>
      <p class="text-sm text-gray-500 mt-1">Withdraw funds from your trading account. All requests undergo AI-powered fraud evaluation.</p>
    </div>

    <!-- Result Banners -->
    <WithdrawalResultBanner
      :show-fraud-notice="showFraudNotice"
      :show-success="showSuccess"
      :eval-result="evalResult"
      @dismiss="dismissResult"
    />

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Method Selector (Left 2/3) -->
      <div class="lg:col-span-2">
        <WithdrawalMethodSelector v-model:selected="selectedMethod" />
      </div>

      <!-- Withdrawal Form (Right 1/3) -->
      <WithdrawalDetailsForm
        v-model:selected-account="selectedAccount"
        v-model:amount="amount"
        v-model:recipient-name="recipientName"
        v-model:recipient-account="recipientAccount"
        :selected-method="selectedMethod"
        :accounts="accounts"
        :loading-accounts="loadingAccounts"
        :current-account="currentAccount"
        :parsed-amount="parsedAmount"
        :calculated-fee="calculatedFee"
        :receive-amount="receiveAmount"
        :amount-error="amountError"
        :can-submit="canSubmit"
        :is-submitting="isSubmitting"
        @submit="handleSubmit"
      />
    </div>
  </div>
</template>
