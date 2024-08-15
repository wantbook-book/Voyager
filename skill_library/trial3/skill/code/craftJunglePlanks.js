async function craftJunglePlanks(bot) {
  // Check if there is a jungle log in the inventory
  const jungleLog = bot.inventory.findInventoryItem(mcData.itemsByName["jungle_log"].id);
  if (!jungleLog) {
    // Mine a jungle log
    await mineBlock(bot, "jungle_log", 1);
  }

  // Check if there is a crafting table in the inventory
  const craftingTable = bot.inventory.findInventoryItem(mcData.itemsByName["crafting_table"].id);
  if (!craftingTable) {
    // Craft a crafting table using the jungle log
    await craftItem(bot, "crafting_table", 1);
  }

  // Place the crafting table near the player
  const craftingTablePosition = bot.entity.position.offset(1, 0, 0);
  await placeItem(bot, "crafting_table", craftingTablePosition);

  // Craft 4 jungle planks using the jungle log and the crafting table
  await craftItem(bot, "jungle_planks", 1, craftingTablePosition);
  bot.chat("4 jungle planks crafted.");
}