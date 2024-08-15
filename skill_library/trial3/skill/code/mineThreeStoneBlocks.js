async function mineThreeStoneBlocks(bot) {
  // Equip the wooden pickaxe
  const woodenPickaxe = bot.inventory.findInventoryItem(mcData.itemsByName["wooden_pickaxe"].id);
  await bot.equip(woodenPickaxe, "hand");

  // Mine 3 stone blocks
  await mineBlock(bot, "stone", 3);
  bot.chat("3 stone blocks mined.");
}