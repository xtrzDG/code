"use client";

/**
 * "Get a number": the owner picks a country, a kind of number and maybe a
 * city, sees the numbers on offer with their monthly price, and takes one
 * after confirming (the API may ask them to confirm it is them first). Where
 * a number needs the business's documents, or this server rents none of
 * that kind, the owner asks our team instead.
 */

import { useState } from "react";

import { useCountries } from "@/api/catalog";
import { describeError } from "@/api/errors";
import { Alert, Button, Modal } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import {
  PHONE_NUMBER_REFUSALS,
  cityQuery,
  initialCountry,
  rentBody,
  type PhoneLineView,
  type PhoneNumberOffer,
  type PhoneNumberOffers,
  type RentedPhoneNumber,
} from "../../_lib/phoneLine";
import { usePhoneLineActions } from "../../_lib/usePhoneLine";
import { NumberOffers, TakeNumberConfirm } from "./NumberOffers";
import { NumberSearchFields, type NumberSearchForm } from "./NumberSearchFields";

export function GetNumberDialog({
  open,
  onClose,
  businessId,
  line,
  onRented,
  onRequested,
}: {
  open: boolean;
  onClose: () => void;
  businessId: string;
  line: PhoneLineView;
  onRented: (number: RentedPhoneNumber) => void;
  onRequested: () => void;
}) {
  const { t, tp } = useI18n();
  const countries = useCountries();
  const list = countries.data?.countries ?? [];
  const actions = usePhoneLineActions(businessId);
  const [form, setForm] = useState<NumberSearchForm>(() => ({
    countryCode: initialCountry(line, list),
    numberType: "local",
    city: "",
  }));
  const [offers, setOffers] = useState<PhoneNumberOffers | null>(null);
  const [chosen, setChosen] = useState<PhoneNumberOffer | null>(null);
  const [error, setError] = useState<unknown>(null);

  const change = (update: Partial<NumberSearchForm>) => {
    setForm((current) => ({ ...current, ...update }));
    setOffers(null);
    setChosen(null);
  };

  const search = async () => {
    setError(null);
    setChosen(null);
    const result = await actions.search.run({
      countryCode: form.countryCode,
      numberType: form.numberType,
      city: cityQuery(form.city),
    });
    if (result.ok) {
      setOffers(result.data);
    } else {
      setError(result.error);
    }
  };

  const take = async () => {
    const body = chosen && offers ? rentBody(chosen, offers) : null;
    if (!body) {
      return;
    }
    setError(null);
    const result = await actions.rent.run(body);
    if (result.ok) {
      onRented(result.data);
      return;
    }
    setError(result.error);
    setChosen(null);
    setOffers(null);
  };

  const askTeam = async () => {
    setError(null);
    const city = cityQuery(form.city);
    const result = await actions.ask.run({
      country_code: form.countryCode,
      number_type: form.numberType,
      ...(city ? { city } : {}),
    });
    if (result.ok) {
      onRequested();
    } else {
      setError(result.error);
    }
  };

  const problem = error ? describeError(error, { t, tp }, undefined, PHONE_NUMBER_REFUSALS) : null;

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title={t("phoneNumbers.dialog.title")}
      description={t("phoneNumbers.dialog.description")}
      footer={
        <Button variant="ghost" onClick={onClose}>
          {t("phoneNumbers.dialog.close")}
        </Button>
      }
    >
      <div className="space-y-5">
        <NumberSearchFields
          form={form}
          onChange={change}
          countries={list}
          selfServeCountries={line.self_serve_countries ?? []}
          isSearching={actions.search.isPending}
          onSearch={() => void search()}
        />
        {problem ? (
          <Alert tone="danger" title={problem.title}>
            {problem.detail}
          </Alert>
        ) : null}
        {offers && chosen ? (
          <TakeNumberConfirm
            offer={chosen}
            offers={offers}
            isTaking={actions.rent.isPending}
            onTake={() => void take()}
            onBack={() => setChosen(null)}
          />
        ) : offers ? (
          <NumberOffers offers={offers} onTake={setChosen} onAskTeam={() => void askTeam()} isAsking={actions.ask.isPending} />
        ) : null}
      </div>
    </Modal>
  );
}
