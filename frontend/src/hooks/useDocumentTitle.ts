import { useEffect } from "react";

export function useDocumentTitle(title?: string) {
  useEffect(() => {
    const prevTitle = document.title;
    if (title) {
      document.title = `${title} | APAAR Central Portal`;
    } else {
      document.title = "APAAR Central Portal | Student Data Management System";
    }
    return () => {
      document.title = prevTitle;
    };
  }, [title]);
}
