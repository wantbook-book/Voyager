async function craftStonePickaxe(bot) {
  // Place the crafting table near the bot
  const craftingTablePosition = bot.entity.position.offset(1, 0, 0);
  await placeItem(bot, "crafting_table", craftingTablePosition);

  // Craft a stone pickaxe using the crafting table
  await craftItem(bot, "stone_pickaxe", 1);
  bot.chat("Stone pickaxe crafted.");
}