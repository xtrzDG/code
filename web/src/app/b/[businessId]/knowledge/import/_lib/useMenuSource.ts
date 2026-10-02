"use client";

import { useId, useRef, useState, type DragEvent, type FormEvent } from "react";

import { api } from "@/api/client";
import { describeError } from "@/api/errors";
import { useApiMutation } from "@/api/hooks";
import type { Schema } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { base64FromDataUrl, checkMenuFile, menuLinkProblem } from "@/lib/knowledge/menuImport";
import { webLinkSchema } from "@/lib/validation";

export type MenuSourceKind = "file" | "link";

type ImportBody = { media_type: string; data_base64?: string; url?: string };

/** Reads a chosen file as base64 (without the data URL prefix). */
function readAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(base64FromDataUrl(String(reader.result ?? "")));
    reader.onerror = () => reject(reader.error ?? new Error("The file could not be read."));
    reader.readAsDataURL(file);
  });
}

/**
 * Where the menu comes from (a file or a link) and reading it: the chosen
 * file or typed link, their errors, and why the reader failed. A link the
 * API cannot read is explained by its reason code.
 */
export function useMenuSource(onImported: (result: Schema<"MenuImportResult">) => void) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const inputId = useId();
  const fileInput = useRef<HTMLInputElement>(null);

  const [source, setSource] = useState<MenuSourceKind>("file");
  const [file, setFile] = useState<{ file: File; mediaType: string } | null>(null);
  const [fileError, setFileError] = useState<MessageKey | null>(null);
  const [link, setLink] = useState("");
  const [linkError, setLinkError] = useState<MessageKey | null>(null);
  const [isDragging, setDragging] = useState(false);
  const [isReading, setReading] = useState(false);
  const [readError, setReadError] = useState<unknown>(null);

  const importMenu = useApiMutation(
    (body: ImportBody) =>
      api.POST("/v1/businesses/{business_id}/knowledge/import", {
        params: { path: { business_id: business.id } },
        body,
      }),
    { errorToast: false },
  );

  const chooseSource = (next: MenuSourceKind) => {
    setSource(next);
    setReadError(null);
  };

  const chooseFile = (chosen: File | undefined) => {
    setReadError(null);
    if (!chosen) {
      return;
    }
    const check = checkMenuFile(chosen);
    if (!check.ok) {
      setFile(null);
      setFileError(check.error);
      return;
    }
    setFileError(null);
    setFile({ file: chosen, mediaType: check.mediaType });
  };

  const onDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setDragging(false);
    chooseFile(event.dataTransfer.files[0]);
  };

  const changeLink = (value: string) => {
    setLink(value);
    setLinkError(null);
  };

  const read = async (event: FormEvent) => {
    event.preventDefault();
    setReadError(null);
    let body: ImportBody;
    if (source === "file") {
      if (!file) {
        setFileError("knowledge.import.errors.fileRequired");
        return;
      }
      setReading(true);
      try {
        body = { media_type: file.mediaType, data_base64: await readAsBase64(file.file) };
      } catch {
        setReading(false);
        setFileError("knowledge.import.errors.fileUnreadable");
        return;
      }
    } else {
      const parsed = webLinkSchema.safeParse(link);
      if (!parsed.success) {
        setLinkError(link.trim() === "" ? "validation.required" : "validation.url");
        return;
      }
      setReading(true);
      body = { media_type: "text/html", url: parsed.data };
    }
    const result = await importMenu.run(body);
    setReading(false);
    if (!result.ok) {
      setReadError(result.error);
      return;
    }
    onImported(result.data);
  };

  /** Back to an empty form for another import. */
  const reset = () => {
    setFile(null);
    setLink("");
    setReadError(null);
    if (fileInput.current) {
      fileInput.current.value = "";
    }
  };

  const linkProblem = source === "link" ? menuLinkProblem(readError) : null;
  const readFailure =
    readError && !linkProblem
      ? describeError(readError, t, { external_service_error: "knowledge.import.errors.service" })
      : null;

  return {
    inputId,
    fileInput,
    source,
    chooseSource,
    file,
    fileError,
    chooseFile,
    onDrop,
    isDragging,
    setDragging,
    link,
    linkError,
    changeLink,
    isReading,
    read,
    reset,
    linkProblem,
    readFailure,
  };
}

export type MenuSource = ReturnType<typeof useMenuSource>;
