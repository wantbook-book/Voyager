async function craftCraftingTable(bot) {
  // Check if there are enough jungle planks in the inventory
  const junglePlanks = bot.inventory.count(mcData.itemsByName["jungle_planks"].id);
  if (junglePlanks < 4) {
    bot.chat("Not enough jungle planks to craft a crafting table.");
    return;
  }

  // Craft a crafting table using jungle planks
  await craftItem(bot, "crafting_table", 1);
  bot.chat("Crafting table crafted.");
}