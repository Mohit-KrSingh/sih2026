import { useEffect } from "react";
import { PRODUCT_NAME, SHORT_DESCRIPTION } from "../brand";

export function useDocumentTitle(title?: string) {
  useEffect(() => {
    const prevTitle = document.title;
    if (title) {
      document.title = `${title} | ${PRODUCT_NAME}`;
    } else {
      document.title = `${PRODUCT_NAME} | ${SHORT_DESCRIPTION}`;
    }
    return () => {
      document.title = prevTitle;
    };
  }, [title]);
}
