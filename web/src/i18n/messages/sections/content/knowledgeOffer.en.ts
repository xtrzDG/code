/**
 * `knowledge.offer.*` texts of bookable offers (services, packages, room
 * types) and the resources that perform them, in English: the reference
 * that ru and ka are typed against.
 */

export const knowledgeOfferEn = {
  offer: {
    nightlyPrice: "Nightly rate, {currency}",
    nightlyPriceHint: "Nights outside every season cost this. Leave empty if it depends on something.",
    durationHint: "5 to 720 minutes: a booking lasts this long.",
    buffer: "Break after, min",
    bufferHint: "Whoever performs it stays busy this long afterwards (cleaning, preparation).",
    performers: "Who performs it",
    performersHint: "Only they are offered for it. Nobody ticked: anyone not tied to a particular service can do it.",
    rooms: "Rooms of this type",
    roomsHint: "A stay of this type is booked in one of these rooms. None ticked: any room booked by the night.",
    noResources: "Nobody to choose yet: add your team, rooms or places first.",
    toResources: "Open Resources and hours",
    resourceOff: "off",
    filter: "Find by name",
    noMatches: "Nobody matches “{query}”",
    selectedCount: { one: "{count} chosen", other: "{count} chosen" },
    seasons: "Seasonal rates",
    seasonsHint: "A night inside a season costs its rate, every year. A season may run over New Year; seasons may not overlap.",
    addSeason: "Add a season",
    seasonTitle: "Season {number}",
    seasonName: "Name",
    seasonNamePlaceholder: "For example: Summer",
    from: "From",
    to: "To",
    day: "Day",
    month: "Month",
    seasonRate: "Per night, {currency}",
    removeSeason: "Remove season {number}",
    noSeasons: "No seasons: every night costs the nightly rate.",
    performedBy: "With {names}",
    roomsList: "Rooms: {names}",
    breakValue: "+{count} min break",
    perNight: "{price} a night",
    seasonsValue: { one: "{count} season", other: "{count} seasons" },
    errors: {
      bufferRange: "0 to 240 minutes",
      seasonDate: "That month has no such day",
      seasonOverlap: "Seasons {first} and {second} share days: a night must have one rate.",
      tooManySeasons: "At most {count} seasons",
    },
  },
} as const;
