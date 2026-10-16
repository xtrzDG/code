import type { Translation } from "../../translate";
import type { onboardingEn } from "./en";
import { profileEditKa } from "./profileEdit.ka";

/** ბიზნესის პროფილის ტექსტები. გასაღებები — როგორც en.ts-ში. */
export const onboardingKa: Translation<typeof onboardingEn> = {
  onboarding: {
    choose: "აირჩიეთ…",
    gaps: {
      times: { one: "{count}-ჯერ", other: "{count}-ჯერ" },
      notReady: { one: "აკლია {count} სავალდებულო პუნქტი", other: "აკლია {count} სავალდებულო პუნქტი" },
    },
    week: {
      closed: "დასვენების დღე",
      opens: "იხსნება",
      closes: "იხურება",
      addInterval: "შესვენების ან მეორე ცვლის დამატება",
      removeInterval: "ინტერვალის მოშორება",
      overnight: "მომდევნო დღის {time}-მდე",
      roundTheClock: "24 საათი",
      copyToAll: "ორშაბათის ყველა დღეზე გადატანა",
    },
    offer: {
      kinds: {
        faq: "კითხვა და პასუხი",
        policy: "წესი",
        menu_item: "კერძი",
        service: "მომსახურება",
        room_type: "ნომრის ტიპი",
        package: "პაკეტი",
        vehicle: "ავტომობილი",
        product: "პროდუქტი",
      },
    },
    booking: {
      noBookings: "თქვენი ნიშა ჯავშნებს არ იღებს: ასისტენტი აგროვებს მოთხოვნებს და მენეჯერს გადასცემს.",
      resourceKinds: {
        table: "მაგიდა",
        room: "ნომერი",
        staff: "სპეციალისტი",
        arena: "არენა ან დარბაზი",
        bay: "სერვისის პოსტი",
        vehicle: "ავტომობილი",
        slot: "დროის სლოტი",
      },
    },
    resources: {
      namePlaceholder: "მაგალითად: არენა 1",
    },
  },
  profileEdit: profileEditKa,
};
