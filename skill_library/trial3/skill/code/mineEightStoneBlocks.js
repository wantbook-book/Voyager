async function mineEightStoneBlocks(bot) {
  // Check if we have a wooden pickaxe equipped
  const woodenPickaxe = bot.inventory.findInventoryItem(mcData.itemsByName["wooden_pickaxe"].id);
  if (!woodenPickaxe) {
    bot.chat("No wooden pickaxe found in the inventory.");
    return;
  }

  // Mine 8 stone blocks
  await mineBlock(bot, "stone", 8);
  bot.chat("8 stone blocks mined.");
}